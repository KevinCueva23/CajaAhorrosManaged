import json
import os
import requests
import zipfile
import io
import csv
import azure.functions as func  # Importar la biblioteca de Azure Functions

# Cargar variables de entorno
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
TENANT_ID = os.getenv("TENANT_ID")


def get_token():
    """ Obtiene el token de autenticación de Microsoft Graph API """
    url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
    body = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "scope": "https://graph.microsoft.com/.default",
        "grant_type": "client_credentials"
    }
    response = requests.post(url, data=body)
    response.raise_for_status()  # Lanza un error si falla la petición
    return response.json().get("access_token")


def defender_agents_report():
    """ Obtiene el reporte de Defender Agents desde Microsoft Graph """
    auth_token = get_token()

    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': "Bearer " + auth_token
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

    response = requests.post("https://graph.microsoft.com/v1.0/deviceManagement/reports/exportJobs", 
                             data=json.dumps(body), headers=headers)
    
    if response.status_code != 200:
        return {"error": "Error al solicitar el reporte", "details": response.text}

    report_id = response.json().get('id')

    # Verificar el estado del reporte
    status = ""
    while status != "completed":
        url = f"https://graph.microsoft.com/beta/deviceManagement/reports/exportJobs('{report_id}')"
        response = requests.get(url, headers=headers)
        status = response.json().get('status')

    # Obtener la URL de descarga
    download_url = response.json().get('url')
    report_response = requests.get(download_url)

    # Descomprimir el archivo ZIP
    with zipfile.ZipFile(io.BytesIO(report_response.content)) as zip_file:
        with zip_file.open(zip_file.namelist()[0]) as csv_file:
            lines = csv_file.read().decode('utf-8').splitlines()
            rows = list(csv.reader(lines))

    # Verificar si todas las filas tienen la misma cantidad de columnas que la primera
    header_length = len(rows[0])
    valid_rows = [row for row in rows[1:] if len(row) == header_length]

    # Crear el diccionario con las filas válidas
    result_dict = [dict(zip(rows[0], row)) for row in valid_rows]

    return result_dict


def main(req: func.HttpRequest) -> func.HttpResponse:
    """ Función de Azure que devuelve el JSON en una respuesta HTTP """
    try:
        result = defender_agents_report()
        return func.HttpResponse(json.dumps(result, indent=4), mimetype="application/json")
    except Exception as e:
        return func.HttpResponse(f"Error: {str(e)}", status_code=500)
