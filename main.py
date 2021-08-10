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

from mongo_utils import db_connection, retrieve_mongo_data
from utils import open_position

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
                        content=f"Successfully Added with key '{insert_status.inserted_id}'")


@app.post("/start/larry_session/", response_description="Start a new larry session")
async def start_larry_session(data: LarrySessionModel):
    larry_session = jsonable_encoder(data)
    mongo_timestamps, mongo_prices = retrieve_mongo_data(db_connection('data'),
                                                         larry_session['cycle_hours'])
    target_entry_price = volatility_breakout_price(prev_high=max(mongo_prices),
                                                   prev_low=min(mongo_prices),
                                                   prev_price=mongo_prices[-1],
                                                   x=larry_session['x'],
                                                   position=larry_session['position'])
    larry_session['target_entry_price'] = target_entry_price
    db = db_connection('larry_sessions')
    db[larry_session['market']].insert_one(larry_session)
    return JSONResponse(status_code=status.HTTP_201_CREATED, content='Successfully Added')


# @app.post("/larry_signal/", response_description="Received a signal")
# async def larry_signal(data: LarrySessionModel):
#     signal_info = jsonable_encoder(data)
#     # sample_info = {
#     #     'strategy_config': {
#     #         "cycle_hours": 12,
#     #         "x": 0.5
#     #     },
#     #     'market': 'ETHUSDT',
#     #     'current_price': 1436.7,
#     #     'timestamp': 1628515521478,
#     #     'position': 'long'
#     # }
#     x = signal_info['strategy_config']['x']
#     cycle_hours = signal_info['strategy_config']['cycle_hours']
#     position = signal_info['position']
#     timestamp = signal_info['timestamp']
#     market = signal_info['market']
#
#     sessions_db = db_connection('larry_sessions')
#
#     matching_conditions = {
#         # 'market': signal_info['market'],
#         'x': x,
#         'cycle_hours': cycle_hours,
#         'position': position
#     }
#
#     sessions = sessions_db[market].find(matching_conditions)
#     for session in sessions:
#         open_position(session, signal_info['current_price'])
#
#     close_timestamp = timestamp + cycle_hours * 60 * 60 * 1000
#     sessions_db[market].update_many(matching_conditions,
#                                     {'$set': {'close_timestamp': close_timestamp}})
#
#     return JSONResponse(status_code=status.HTTP_200_OK, content='Successfully Started Positions')


if __name__ == "__main__":
    # start_consuming()
    uvicorn.run(app, host="0.0.0.0", port=8000)
