import azure.functions as func
import logging
 
app = func.FunctionApp()
 
@app.route(route="req")
@app.read_blob(arg_name="obj", path="samples/{id}", 
               connection="STORAGE_CONNECTION_STRING")
def main(req: func.HttpRequest, obj: func.InputStream):
    logging.info(f'Python HTTP-triggered function processed: {obj.read()}')