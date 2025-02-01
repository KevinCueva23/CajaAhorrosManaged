import json
import requests
import zipfile
import io
import csv
import azure.functions as func
import os

def get_token():
    url = f"https://login.microsoftonline.com/{os.environ['TENANT_ID']}/oauth2/v2.0/token"
    body = {
        "client_id": os.environ['CLIENT_ID'],
        "client_secret": os.environ['CLIENT_SECRET'],
        "scope": "https://graph.microsoft.com/.default",
        "grant_type": "client_credentials"
    }
    response = requests.post(url, data=body)
    return response.json().get("access_token")

def defender_agents_report():
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
        return {"error": "Error al solicitar el informe", "details": response.text}

    report_id = response.json().get('id')
    status = ""

    while status != "completed":
        url = f"https://graph.microsoft.com/beta/deviceManagement/reports/exportJobs('{report_id}')"
        response = requests.get(url, headers=headers)
        status = response.json().get('status')

    download_url = response.json().get('url')
    report_response = requests.get(download_url)

    with zipfile.ZipFile(io.BytesIO(report_response.content)) as zip_file:
        with zip_file.open(zip_file.namelist()[0]) as csv_file:
            lines = csv_file.read().decode('utf-8').splitlines()
            rows = list(csv.reader(lines))

    header_length = len(rows[0])
    valid_rows = [row for row in rows[1:] if len(row) == header_length]

    result_dict = {row[0]: dict(zip(rows[0], row)) for row in valid_rows}

    return result_dict

def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        result = defender_agents_report()
        return func.HttpResponse(json.dumps(result, indent=4), mimetype="application/json")
    except Exception as e:
        return func.HttpResponse(f"Error: {str(e)}", status_code=500)
