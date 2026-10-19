import os
import oracledb
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")
oracledb.init_oracle_client(
    lib_dir=r"C:\oraclexe\instantclient_19_32"
)





def get_connection():
    return oracledb.connect(
        user=os.environ["ORACLE_USER"],
        password=os.environ["ORACLE_PASSWORD"],
        host=os.environ.get("ORACLE_HOST", "localhost"),
        port=int(os.environ.get("ORACLE_PORT", "1521")),
        service_name=os.environ["ORACLE_SERVICE"],
    )