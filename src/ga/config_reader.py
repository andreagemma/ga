# libs/config/config_reader.py

import os
import ast
import configparser
try:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.exc import SQLAlchemyError
except:
    pass

class ConfigReader:
    def __init__(self, ini_file=None, db_url=None, db_query=None, use_env=True, order=['ini','db','env']):
        self.config = configparser.ConfigParser()
        self.use_ini = ini_file is not None        
        if self.use_ini:
            self.config.read(ini_file)
            
        self.use_db = db_url is not None        
        self.db_url = db_url        
        self.db_query = db_query or "SELECT value FROM settings WHERE name = :name"
        self.db_session = None
        
        self.use_env = use_env

        if self.use_db and self.db_url:
            self._init_db()
        self.order = order

    def items(self):
        for sec in self.config.sections():
            for name, value in self.config.items(sec):
                yield sec, name, value

    def _init_db(self):
        try:
            engine = create_engine(self.db_url)
            Session = sessionmaker(bind=engine)
            self.db_session = Session()
        except SQLAlchemyError as ex:
            print(f"Error initializing database connection: {ex}")

    def _get_from_db(self, section, name):
        if not self.use_db:
            return None
        if not self.db_session:
            return None
        try:
            result = self.db_session.execute(self.db_query, {'name': name, "section": section}).fetchone()
            return result[0] if result else None
        except SQLAlchemyError as ex:
            print(f"Error fetching {name} from database: {ex}")
            return None

    def _get_from_ini(self, section, name):
        if not self.use_ini:
            return None
        return self.config.get(section, name, fallback=None)

    def _get_from_env(self, name):
        if not self.use_env:
            return None
        return os.getenv(name)

    def get(self, name, default=None, section='DEFAULT'):
        value = None
        for provider in self.order:
            if provider == "ini":
                value = self._get_from_ini(section, name)
            elif provider == "db":
                value = self._get_from_db(section, name)
            elif provider == "env":
                if section.upper()=="DEFAULT":
                    value = self._get_from_env(name)
                else:
                    value = self._get_from_env(section+"_"+name)
        return value.strip() if value is not None else default

    def getint(self, name, default=None, section='DEFAULT'):
        value = self.get(name, section=section, default=default)
        if isinstance(value, int):
            return value
        return int(value) if value is not None else default

    def getboolean(self, name, default=None, section='DEFAULT'):
        value = self.get(name, section=section, default=default)
        if isinstance(value, bool):
            return value
        return value.lower() in ('true', '1', 'yes') if value is not None else default

    def getfloat(self, name, default=None, section='DEFAULT'):
        value = self.get(name, section=section, default=default)
        if isinstance(value, float):
            return value
        return float(value) if value is not None else default

    def getlist(self, name, default=None, section='DEFAULT'):
        value = self.get(name, section=section, default=default)
        if isinstance(value, list):
            return value
        return ast.literal_eval(value) if value is not None else default

    def getset(self, name, default=None, section='DEFAULT'):        
        value = self.get(name, section=section, default=default)
        if isinstance(value, set):
            return value
        return set(ast.literal_eval(value)) if value is not None else default

    def gettuple(self, name, section='DEFAULT', default=None):
        value = self.get(name, section=section, default=default)
        if isinstance(value, tuple):
            return value
        return tuple(ast.literal_eval(value)) if value is not None else default

    def getdict(self, name, section='DEFAULT', default=None):
        value = self.get(name, section=section, default=default)
        if isinstance(value, dict):
            return value
        return dict(ast.literal_eval(value)) if value is not None else default