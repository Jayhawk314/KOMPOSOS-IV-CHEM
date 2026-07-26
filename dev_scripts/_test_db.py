import sqlite3

conn = sqlite3.connect('data/cache/mof_linkers/mof_linkers_22.db')
cursor = conn.cursor()

cursor.execute('SELECT COUNT(*) FROM linkers')
count = cursor.fetchone()[0]
print(f'Linkers in DB: {count}')

if count > 0:
    cursor.execute('SELECT smiles, formula FROM linkers LIMIT 3')
    for row in cursor:
        print(f'  {row[1]}: {row[0][:60]}...')
else:
    print('Database is empty!')

conn.close()
