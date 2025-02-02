import json
import requests
import zipfile
import io
import csv
import azure.functions as func
import os


print ('TENANT_ID:', os.environ['TENANT_ID'])
