# vim: tw=100 foldmethod=indent
import sqlite3
import json
from addict import Dict

from alise.database import Base
from alise.logsetup import logger

# vega_db = VegaUsers()


class LastPage(Base):
    SCHEMA = ["""create table if not exists lastpage (session TEXT, url TEXT)"""]

    def store(self, session, url):
        try:
            con = sqlite3.connect(self.dbfile)
            cur = con.cursor()

            cur.execute(
                "INSERT OR REPLACE into lastpage values(?, ?) ",
                (session, url.__str__()),
            )
            con.commit()
            cur.close()
        except sqlite3.OperationalError as e:
            logger.error("SQL insert error: %s", str(e))
            raise

    def get(self, session):
        try:
            con = sqlite3.connect(self.dbfile)
            cur = con.cursor()

            res = cur.execute(
                "SELECT url FROM lastpage where session=? ", [session]
            ).fetchall()
            con.commit()
            cur.close()
            return res

        except sqlite3.OperationalError as e:
            logger.error("SQL insert error: %s", str(e))
            raise


class DatabaseUser(Base):
    SCHEMA = [
        "CREATE table if not exists int_user (session_id TEXT, identity TEXT, jsonstr JSON)",
        "CREATE table if not exists ext_user (session_id TEXT, identity TEXT, jsonstr JSON)",
        "CREATE table if not exists sites (name TEXT, comment TEXT)",
    ]

    def __init__(self, site_name):
        self.site_name = site_name
        super().__init__()

        # each identity consists of
        # - jsondata (= request.user)
        self.int_id = Dict() 
        self.ext_ids = []

    def store_internal_user(self, jsondata, session_id):
        self.int_id = jsondata
        if not self._is_user_in_db(self.int_id.identity, "int"):
            self.store_user(self.int_id, "int", session_id)
        else:
            # FIXME: update the user!!
            logger.warning("not storing user, as we have that already")

    def store_external_user(self, jsondata, session_id):
        self.ext_ids.append(Dict())
        self.ext_ids[-1] = jsondata
        if not self._is_user_in_db(self.ext_ids[-1].identity, "ext"):
            self.store_user(self.ext_ids[-1], "ext", session_id)
        else:
            # FIXME: update the user!!
            logger.warning("not storing user, as we have that already")

    def store_user(self, jsondata, location, session_id):
        try:
            identity = jsondata.identity.__str__()
            jsonstr = json.dumps(jsondata, sort_keys=True, indent=4)
        except AttributeError as e:
            logger.error(f"cannot find attribute:   {e}")
            logger.error(json.dumps(jsondata, sort_keys=True, indent=4))
            raise

        self._db_query(
            f"INSERT OR REPLACE into {location}_user values(?, ?, ?)",
            (
                session_id,
                identity,
                jsonstr,
            ),
        )
    def get_session_id_by_user_id(self, identity, location="int"):
        short_location = location[0:3]
        # logger.debug(f"returning session_id for user {identity}")
        rv = self.get_user(identity, db_key="identity", location=short_location)
        # logger.debug(rv)
        return  rv.session_id

    def get_session_id_by_internal_user_id(self, identity):
        logger.debug(f"returning session_id for user {identity}")
        rv = self.get_user(identity, db_key="identity", location="int")
        # logger.debug(rv)
        return  rv.sesion_id

    def load_all_identities(self, session_id):
        self.int_id = self.get_user(session_id, "session_id", "int")
        self.ext_ids = self.get_users(session_id, "session_id", "ext")
        # logger.debug(F"self.int_id: {self.int_id}")


    def get_internal_user(self, identity):
        return self.get_user(identity, db_key="identity", location="int")

    def get_external_user(self, identity):
        return self.get_users(identity, db_key="identity", location="ext")

    def get_user(self, value, db_key, location):
        rv = self.get_users(value, db_key, location)[-1]
        # logger.debug(f"rv: {rv}")
        return  rv


    def get_users(self, value, db_key, location):
        # logger.debug(f"db_key: {db_key}")
        keys = ["session_id", "identity", "jsonstr"]
        if db_key not in keys:
            logger.error("Key not found in internal database")
            raise Exception
        # logger.debug(f"DB QUERY: SELECT * from {location}_user WHERE {db_key}={value}")
        res = self._db_query(f"SELECT * from {location}_user WHERE {db_key}=?", [value])
        if len(res) == 0:
            return Dict()
        logger.debug(f"length of results: {len(res)} - {location}")
        rv = []
        for r in res:
            rv.append(Dict())
            for k in keys:
                rv[-1][k] = r[k]
            rv[-1].jsondata = Dict(json.loads(rv[-1].jsonstr))
            del(rv[-1].jsonstr)
        return rv

    def _is_user_in_db(self, identity, location):
        rv = self.get_users(identity, db_key="identity", location=location)
        if len(rv) < 1:
            logger.debug(f"Could not find user {identity} in db")
            return False
        logger.debug(f"found user {identity} in db")
        return True

    def get_int_id(self):
        return self.int_id.identity