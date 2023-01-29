from brownie import network
import pandas as pd
from requests import HTTPError
from scripts.utils.utils import setup_database, get_kafka_producer, get_kafka_consumer
from scripts.utils.interfaces import get_price_oracle
import time, os, sys, json
from datetime import datetime


def get_tokens(db_engine):
    query = "SELECT pair, MAX(tokenAddress) AS tokenAddress FROM metadata_oracles GROUP BY pair"
    df_assets = pd.read_sql(query, con=db_engine)
    return df_assets


def get_new_frame(oracle_contract, list_pairs):
    list_pairs_2 = list_pairs.copy()
    addresses = [i for i in list_pairs_2['tokenAddress'].values]
    try:
        assets_new_prices = oracle_contract.getAssetsPrices(addresses)
    except HTTPError as e:
        if str(e)[:3] == '429':
            sys.exit(13)
    serie_prices = pd.Series(list(assets_new_prices), copy=False)
    list_pairs_2['prices'] = serie_prices
    list_pairs_2.drop(columns=["tokenAddress"], inplace=True)
    list_pairs_2 = [{list_pairs_2.columns[j]: i[j+1] for j in range(len(list_pairs_2.columns))} for i in list_pairs_2.itertuples()]
    return list_pairs

def produce_with_kafka(producer, prices):
    for price in prices:
        producer.send(topic=os.environ['TOPIC_ORACLES'], value=price)

def main():

    db_engine = setup_database()
    producer = get_kafka_producer()
    consumer_blocks = get_kafka_consumer(os.environ['TOPIC_BLOCKS'], group_id=os.environ['CONSUMER_GROUP'], auto_offset_reset='latest')
    pair_address = get_tokens(db_engine)[:2]
    oracle_contract = get_price_oracle()
    for msg in consumer_blocks:
        block_num = json.loads(msg.value)['block_no']
        pair_address['block_num'] = block_num
        block_prices = get_new_frame(oracle_contract, pair_address)
        produce_with_kafka(producer, block_prices)

        # length_before = df_record.shape[0]
        # df_record = pd.concat([df_record, df_actual_prices])
        # df_record = df_record.groupby(['pair', 'tokenAddress', 'prices'], as_index=False).min()
        # df_record.sort_values(by=['block_num'], ascending=True, inplace=True)
        # length_after = df_record.shape[0]
        # difference = length_after - length_before
        # if difference > 0:
        #     value_to_record = df_record.tail(difference)
        #     produce_with_kafka(producer, value_to_record)
        #     df_record = df_record.groupby(['pair', 'tokenAddress'], as_index=False).max()


