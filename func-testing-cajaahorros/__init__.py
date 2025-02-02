import logging
import os
import azure.functions as func
 
 
def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')
 
    name = req.params.get('name')
    if not name:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            name = req_body.get('name')
 
    if name:
        return func.HttpResponse(f"Hello, {name}. This HTTP triggered function executed successfully.")
    else:
        print("Tenant:",os.environ['TENANT_ID'])
        print("Client:",os.environ['CLIENT_ID'])
        print("Secret:",os.environ['CLIENT_SECRET'])
        return func.HttpResponse(
             "Esta cosa no funciona :( pipipi)",
             status_code=200
        )
 