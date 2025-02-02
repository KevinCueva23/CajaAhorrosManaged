import logging
import os
import json
import requests
import zipfile
import io
import csv
import azure.functions as func



def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')
    print("Hola")
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
        print("get_token: ", get_token())
        
        return func.HttpResponse(
             print("Hola"),
             status_code=200
        )


