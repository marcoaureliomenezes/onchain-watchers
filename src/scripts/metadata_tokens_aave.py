
import sys, os
from brownie import interface
import pandas as pd
from requests import HTTPError
from scripts.utils.utils import setup_database, table_exists
from scripts.utils.interfaces import get_aave_pool, get_indexes_datatypes


def get_reserve_tokens(token):
    pool_contract = get_aave_pool()
    list_type_tokens = ["aTokenAddress", "stableDebtTokenAddress", "variableDebtTokenAddress"]
    res = get_indexes_datatypes(list_type_tokens)
    tokens = [pool_contract.getReserveData(token)[res[type_token]] for type_token in list_type_tokens]
    return {"tokenAddress": token, **{list_type_tokens[i]: tokens[i] for i in range(len(tokens))}}


def get_ERC20_metadata(token):
    ERC20_contract = interface.IERC20(token)
    res = dict(tokenAddress = token, decimals = ERC20_contract.decimals())
    try:
        res['name'] = ERC20_contract.name()
        res['symbol'] = ERC20_contract.symbol()

    except OverflowError as e:
        print(f"Error with token {token}")
        res['name'] = None
        res['symbol']  = None
    return res


def find_missing_tokens(new_tokens, db_engine, table_name):
    df_new_tokens = pd.DataFrame(new_tokens, columns=['token_address'])
    df_recorded_tokens = pd.read_sql_query(f"SELECT tokenAddress FROM {table_name}", con=db_engine)
    df_tokens = pd.merge(df_new_tokens, df_recorded_tokens, left_on='token_address', right_on='tokenAddress', how='left')
    token_missing = df_tokens.loc[df_tokens['tokenAddress'].isnull(), 'token_address'].values
    return token_missing


def update_metadata_tokens_aave(pool_contract, db_engine, table_name):
    aave_tokens = pool_contract.getReservesList()
    if table_exists(db_engine, table_name):
        aave_tokens = find_missing_tokens(aave_tokens, db_engine, table_name)
        if len(aave_tokens) == 0: 
            return "UPDATED"
    try:
        df_erc20_data = pd.DataFrame([get_ERC20_metadata(token) for token in aave_tokens])
        df_reserve_data = pd.DataFrame([get_reserve_tokens(token) for token in aave_tokens])
        print(df_reserve_data)
    except HTTPError as e:
        print(e.response)
        sys.exit(13)
    df_token_metadata = pd.merge(df_erc20_data, df_reserve_data, on="tokenAddress", how="left")
    df_token_metadata.to_sql(table_name, con=db_engine, if_exists='append', index=False)
    return 'SUCCESS'
 

def main():
    """This module has the intent of interact with AAVE Pool contracts, V2 and V3, and get some
    metadata about the tokens which are borrowed and lended in the protocol. For each ERC20 used
    by the protocol, there are 3 different kind of tokens.
    """
    db_engine = setup_database()
    table_name = os.environ['TABLE_TOKENS_AAVE']
    aave_pool_contract = get_aave_pool()
    metadata_assets = update_metadata_tokens_aave(aave_pool_contract, db_engine, table_name)
    print(metadata_assets)




