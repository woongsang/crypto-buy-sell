import uvicorn
from dotenv import dotenv_values
from fastapi import FastAPI
from fastapi.encoders import jsonable_encoder
from pymongo import MongoClient
from starlette import status
from starlette.responses import JSONResponse

from buy_strategies import volatility_breakout_price
from kafka_consumer import start_consuming
from models import ExchangeAccountModel, LarrySessionModel

from mongo_utils import db_connection
from utils import initialize_larry_session

app = FastAPI()
config = dotenv_values(".env")

mongo_client = MongoClient(f"{config['MONGO_DB_HOST']}:{config['MONGO_DB_PORT']}/",
                           username=config['MONGO_DB_USER'],
                           password=config['MONGO_DB_PASSWORD'])


@app.get("/")
async def read_root():
    return {"Hello": "World"}


@app.post("/add/exchange_account/", response_description="Add new exchange account")
async def add_exchange_account(data: ExchangeAccountModel):
    exchange_account = jsonable_encoder(data)
    db = db_connection('exchange_accounts')
    insert_status = db[exchange_account['exchange_name']].insert_one(exchange_account)
    return JSONResponse(status_code=status.HTTP_201_CREATED,
                        content=f"Successfully Added with id '{insert_status.inserted_id}'")


@app.post("/start/larry_session/", response_description="Start a new larry session")
async def start_larry_session(data: LarrySessionModel):

    larry_session = jsonable_encoder(data)
    initialize_larry_session(larry_session)

    return JSONResponse(status_code=status.HTTP_201_CREATED, content='Successfully Added')


if __name__ == "__main__":
    start_consuming()
    uvicorn.run(app, host="0.0.0.0", port=8090)
