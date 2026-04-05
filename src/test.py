from ga.io.engine import EngineDuckDB
from ga.io.gata_frame import GataFrame
from ga.io.data_schema import DataSchema
from pathlib import Path
import geopandas as gpd

path_doc = Path(r"d:/Documenti/Lavoro")
path_mobito1000 = path_doc / Path(r"RomaTre/FCD/fcd_server/data/sources/mobito/mobito_1000/fcd.parquet")
path_viasat = Path(r"/mnt/hdd/dati/dati_fcd/viasat/2510/fcd.csv")
path_single = path_mobito1000 / Path(r"id_veh_group=0/part-00021-02322d2c-29c9-4667-a2f7-f1de21e83d22.c000.snappy.parquet")
path_roma = path_doc / Path(r"RM1/Flagship/SW/model4italy/m4i_package/dati/roma/files")
path_link = path_roma / Path(r"links.gpkg|layername=links")
jdbc_link = f"postgresql://postgres:lDvdc15dcd5@192.168.133.80:5432/m4i?table=links&schema=eur2"

test_path = path_doc / Path(r"_Codice\WS Altri Linguaggi\Python\ModuliPython\ga\src\ga\io\example.csv")
with EngineDuckDB.connect(file_based=False) as conn:
    file = test_path
    gf: GataFrame | None = conn.read(file)
    if gf and not gf.empty:
        gf.show(5)
        gf.printSchema()
        schema_filename = file.as_posix()+".schema.json"
        schema: DataSchema = DataSchema.from_json_file(schema_filename)
        print(schema)
        gf.apply_schema(schema,inplace=True)
        gf.show(5)
        gf.printSchema()

        df = gf.toPandas()
        print(df.head(5))
        
        gdf = gpd.GeoDataFrame(
            df.drop(columns=["geom"]),
            geometry=gpd.GeoSeries.from_wkt(df["geom"]),
            crs="EPSG:4326"   # metti il CRS corretto
        )
        print(gdf.head())
        

