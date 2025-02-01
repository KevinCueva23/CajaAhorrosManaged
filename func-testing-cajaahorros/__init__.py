import logging
import json
import requests
import zipfile
import io
import csv
import os  # 📌 Importamos os para leer variables de entorno
import azure.functions as func

# 🔒 Obtener credenciales desde variables de entorno
CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
TENANT_ID = os.getenv('TENANT_ID')

if not CLIENT_ID or not CLIENT_SECRET or not TENANT_ID:
    logging.error("❌ ERROR: Variables de entorno faltantes. Verifica en Azure.")
    raise Exception("No se encontraron las variables de entorno necesarias.")

def get_token():
    """ Obtiene el token de autenticación de Microsoft Graph """
    try:
        url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
        body = {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "scope": "https://graph.microsoft.com/.default",
            "grant_type": "client_credentials"
        }
        response = requests.post(url, data=body)
        response.raise_for_status()  
        return response.json().get("access_token")
    except requests.exceptions.RequestException as e:
        logging.error(f"Error obteniendo token: {str(e)}")
        return None

def defender_agents_report():
    """ Genera y descarga el reporte de Defender Agents desde Microsoft Graph """
    auth_token = get_token()
    if not auth_token:
        raise Exception("No se pudo obtener el token de autenticación.")

    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': f"Bearer {auth_token}"
    }

    body = {
        "reportName": "DefenderAgents",
        "select": [
            "DeviceId", "_ManagedBy", "DeviceName", "DeviceState", "PendingFullScan", "PendingReboot",
            "PendingManualSteps", "PendingOfflineScan", "CriticalFailure",
            "MalwareProtectionEnabled", "RealTimeProtectionEnabled", "NetworkInspectionSystemEnabled",
            "SignatureUpdateOverdue", "QuickScanOverdue", "FullScanOverdue", "RebootRequired",
            "FullScanRequired", "EngineVersion", "SignatureVersion", "AntiMalwareVersion",
            "LastQuickScanDateTime", "LastFullScanDateTime", "LastQuickScanSignatureVersion",
            "LastFullScanSignatureVersion", "LastReportedDateTime", "UPN", "UserEmail", "UserName"
        ]
    }

    try:
        response = requests.post("https://graph.microsoft.com/v1.0/deviceManagement/reports/exportJobs", 
                                 data=json.dumps(body), headers=headers)
        response.raise_for_status()

        report_data = response.json()
        report_id = report_data.get('id')

        if not report_id:
            logging.error(f"❌ Error: La API no devolvió un 'id'. Respuesta: {report_data}")
            raise Exception("La API de Microsoft Graph no devolvió un ID de reporte válido.")

        # Esperar a que el reporte esté listo
        status = ""
        while status != "completed":
            url = f"https://graph.microsoft.com/beta/deviceManagement/reports/exportJobs('{report_id}')"
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            status = response.json().get('status', 'unknown')

            logging.info(f"⌛ Esperando... Estado: {status}")

        # Obtener la URL de descarga
        download_url = response.json().get('url')
        if not download_url:
            raise Exception("No se pudo obtener la URL de descarga del reporte.")

        report_response = requests.get(download_url)
        report_response.raise_for_status()

        with zipfile.ZipFile(io.BytesIO(report_response.content)) as zip_file:
            with zip_file.open(zip_file.namelist()[0]) as csv_file:
                lines = csv_file.read().decode('utf-8').splitlines()
                rows = list(csv.reader(lines))

        header_length = len(rows[0])
        valid_rows = [row for row in rows[1:] if len(row) == header_length]
        result_dict = {row[0]: dict(zip(rows[0], row)) for row in valid_rows}

        return result_dict

    except requests.exceptions.RequestException as e:
        logging.error(f"❌ Error en la solicitud a Microsoft Graph: {str(e)}")
        raise Exception(f"Error en la solicitud a Microsoft Graph: {str(e)}")


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('🚀 Azure Function ejecutando Defender Agents Report.')

    try:
        result = defender_agents_report()
        return func.HttpResponse(
            json.dumps(result, indent=4),
            mimetype="application/json",
            status_code=200
        )
    except Exception as e:
        logging.error(f"❌ Error ejecutando el reporte: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            mimetype="application/json",
            status_code=500
        )
