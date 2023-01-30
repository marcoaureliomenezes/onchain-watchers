from brownie import network
import pandas as pd
from requests import HTTPError
from scripts.utils.utils import setup_database, get_kafka_producer, get_kafka_consumer
from scripts.utils.interfaces import get_price_oracle
import time, os, sys, json
from datetime import datetime


def get_tokens(db_engine, version):
    query = f"SELECT * FROM erc_20_tokens WHERE description = 'AAVE V{version}'"
    df_assets = pd.read_sql(query, con=db_engine)
    return df_assets


def get_new_frame(oracle_contract, df_tokens_address, block_no):

    list_token_addresses = list(df_tokens_address["tokenAddress"].values)
    list_symbols = list(df_tokens_address["symbol"].values)
    assets_new_prices = oracle_contract.getAssetsPrices(list_token_addresses)
    res = [(list_symbols[i], assets_new_prices[i], block_no) for i in range(len(assets_new_prices))]
    df = pd.DataFrame(res, columns=["token", "price", "block_no"])
    return df


def produce_with_kafka(producer, prices):
    for price in prices:
        producer.send(topic=os.environ['TOPIC_ORACLES'], value=price)

def aggregator(df_aave_prices, df_price_cumulator):

    df_price_cumulator = pd.concat([df_aave_prices, df_price_cumulator])
    df_price_cumulator = df_price_cumulator.groupby(['token', 'price']).min()
    df_price_cumulator.sort_values(by=['block_no', 'token'], inplace=True)
    df_price_cumulator.reset_index(inplace=True)
    return df_price_cumulator

def main(version):
    db_engine = setup_database()
    producer = get_kafka_producer()
    topic_blocks = f"{network.show_active()}_{os.environ['TOPIC_INPUT']}"
    consumer_group = os.environ['CONSUMER_GROUP']
    consumer_blocks = get_kafka_consumer(topic_blocks, group_id=consumer_group, auto_offset_reset='latest')
    df_tokens_address = get_tokens(db_engine, version)
    oracle_contract = get_price_oracle(version)
    df_price_cumulator = pd.DataFrame([], columns=["token", "price", "block_no"])
    offset_counter = 0
    for msg in consumer_blocks:
        block_number = json.loads(msg.value)['number']
        df_aave_prices = get_new_frame(oracle_contract, df_tokens_address, block_number)
        df_price_cumulator = aggregator(df_aave_prices, df_price_cumulator)

        # df_price_cumulator = pd.concat([df_price_cumulator, df_aave_prices])
        # df_price_cumulator.drop_duplicates(inplace=True)
        # df_price_cumulator.sort_values(by=['token'], inplace=True)
        print(df_price_cumulator)
        offset_counter += 1
        #produce_with_kafka(producer, block_prices)



