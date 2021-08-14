import uvicorn
from dotenv import dotenv_values
from fastapi import FastAPI
from fastapi.encoders import jsonable_encoder
from pymongo import MongoClient
from starlette import status
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

from kafka_consumer import start_consuming
from models import ExchangeAccount, LarrySession

from mongo_utils import db_connection
from utils import initialize_larry_session

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

config = dotenv_values(".env")

mongo_client = MongoClient(f"{config['MONGO_DB_HOST']}:{config['MONGO_DB_PORT']}/",
                           username=config['MONGO_DB_USER'],
                           password=config['MONGO_DB_PASSWORD'])


@app.get("/")
async def read_root():
    return {"Hello": "World"}


@app.post("/add/exchange_account/", response_description="Add new exchange account")
async def add_exchange_account(data: ExchangeAccount):
    exchange_account = jsonable_encoder(data)
    db = db_connection('exchange_accounts')
    insert_status = db[exchange_account['exchange_name']].insert_one(exchange_account)
    return JSONResponse(status_code=status.HTTP_201_CREATED,
                        content=f"Successfully Added with id '{insert_status.inserted_id}'")


@app.post("/start/larry_session/", response_description="Start a new larry session")
async def start_larry_session(data: LarrySession):

    larry_session = jsonable_encoder(data)
    initialize_larry_session(larry_session)

    return JSONResponse(status_code=status.HTTP_201_CREATED, content='Successfully Added')


@app.post("/request_api/", response_description="add request")
async def add_api_request(data: RequestApiModel):
    request_api = jsonable_encoder(data)
    db = db_connection('web_config')

    db['request'].delete_many({'id': request_api['id']})

    insert_status = db['request'].insert_one(request_api)

    return JSONResponse(status_code=status.HTTP_201_CREATED,
                        content=f"Successfully Added with id '{insert_status.inserted_id}'")


@app.get("/request_api/", response_description="add request")
async def add_api_request():
    db = db_connection('web_config')
    results = db.get_collection('request').find()
    request_list = []
    for result in results:
        request_list.append({
            'id': result['id'],
            'url': result['url'],
            'elements': result['elements']
        })

    return request_list


if __name__ == "__main__":
    start_consuming()
    uvicorn.run(app, host="0.0.0.0", port=8090)
