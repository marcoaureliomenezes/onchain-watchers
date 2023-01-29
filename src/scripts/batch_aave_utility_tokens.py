import sys, logging
import pandas as pd
from requests import HTTPError
from brownie import interface, config, network
from scripts.utils.utils import setup_database, table_exists
from scripts.utils.interfaces import get_aave_pool, get_indexes_datatypes



def get_reserve_tokens(token):
    pool_contract = get_aave_pool()
    list_type_tokens = ["aTokenAddress", "stableDebtTokenAddress", "variableDebtTokenAddress"]
    res = get_indexes_datatypes(list_type_tokens)
    tokens = [pool_contract.getReserveData(token)[res[type_token]] for type_token in list_type_tokens]
    return {"tokenAddress": token, **{list_type_tokens[i]: tokens[i] for i in range(len(tokens))}}


def main(version):
    db_engine = setup_database()
    aave_utility_table = "aave_utility_tokens"
    aave_contract = get_aave_pool(version)
    df_erc20_aave = None
    
    df_utility_aave = pd.DataFrame([get_reserve_tokens(token) for token in df_erc20_aave])
    df_utility_aave.to_sql(aave_utility_table, con=db_engine, if_exists='append', index=False)
