import pyodbc

def get_connection(): #assuming windows authentication
    return pyodbc.connect(
        "DRIVER={ODBC Driver 18 for SQL Server};"
        "SERVER=localhost;"
        "DATABASE=OlistDW;"
        "Trusted_Connection=yes;"
        "TrustServerCertificate=yes;"
    )