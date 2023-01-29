import logging
import pandas as pd
from brownie import interface, config, network
from scripts.utils.utils import setup_database, table_exists
from scripts.utils.interfaces import get_aave_pool


# LINK OFFICIAL

def main(version):
    db_engine = setup_database()
    erc20_table = "erc_20_tokens"
    link_token = config["networks"][network.show_active()]
    aave_contract = get_aave_pool(version)
    aave_tokens = aave_contract.getReservesList()
    # if table_exists(db_engine, erc20_table):
    #     aave_tokens = find_missing_tokens(aave_tokens, db_engine, erc20_table)
    #     if len(aave_tokens) == 0:
    #         logging.info(f"Information about tokens AAVE V{version} already updated")
    #         return
    # df_erc20_data = pd.DataFrame([get_ERC20_metadata(token) for token in aave_tokens])
    # df_erc20_data["description"] = f"AAVE V{version}"
    # df_erc20_data.to_sql(erc20_table, con=db_engine, if_exists='append', index=False)