import logging
import pandas as pd
from brownie import interface
from scripts.utils.utils import setup_database, table_exists
from scripts.utils.interfaces import get_aave_pool

logging.basicConfig(level='INFO')


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


def main(version):
    db_engine = setup_database()
    erc20_table = "erc_20_tokens"
    aave_contract = get_aave_pool(version)
    aave_tokens = aave_contract.getReservesList()
    if table_exists(db_engine, erc20_table):
        aave_tokens = find_missing_tokens(aave_tokens, db_engine, erc20_table)
        if len(aave_tokens) == 0:
            logging.info(f"Information about tokens AAVE V{version} already updated")
            return
    df_erc20_data = pd.DataFrame([get_ERC20_metadata(token) for token in aave_tokens])
    df_erc20_data["description"] = f"AAVE V{version}"
    df_erc20_data.to_sql(erc20_table, con=db_engine, if_exists='append', index=False)
    