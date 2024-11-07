

import json
import logging
import datetime as dt
from pathlib import Path
import uuid
import psycopg2
import os


class DBHelperPostgress :
    """
    Class to manage socket connections for users
    """

    def __init__(self,connection_data:dict=None):
        self.log = logging.getLogger(__name__) 
        self.host       =None
        self.port       =None
        self.database   =None
        self.user       =None
        self.password   =None       
        if connection_data is None:
            self._load_ddbb_config ()
        else:
            self.host       =connection_data['host']
            self.port       =connection_data['port']
            self.database   =connection_data['database']
            self.user       =connection_data['user']
            self.password   =connection_data['password']   
            
    def _load_ddbb_config(self):
        dbcfg=os.environ['DDBB_CONFIG']
        if dbcfg is not None: 
            dbcfg=json.loads(dbcfg)
            self.host       =dbcfg['host']
            self.port       =dbcfg['port']
            self.database   =dbcfg['database']
            self.user       =dbcfg['user']
            self.password   =dbcfg['password']             
        
        elif dbcfg is None:        
            self.host       =os.environ['host']
            self.port       =os.environ['port']
            self.database   = os.environ.get('database')
            if self.database is None:
                self.database   =os.environ.get('db')
            if self.database is None:   
                raise Exception("configuration error. Please provide database name in key 'database' or in key 'db") 
            self.user       =os.environ['user']
            self.password   =os.environ['password']                           

    def connect(self):
        """ Connect to the database server . Primarily to postgress"""
        conn = psycopg2.connect(
            host=self.host,
            port=self.port,
            database=self.database,
            user=self.user,
            password=self.password)
        return conn


    def insert_connection(self, participant_id,socket_id,space="PUBLIC",shared_conn=None):
        """ insert a new connection  """

        sql = """INSERT INTO client_connections(participant_id,socket_id,space)
                VALUES(%s,%s,%s);"""
        conn = None        
        myconn=False  
        id = None
        try:
            myconn,conn=self._connection_get(shared_conn=shared_conn)
            cur = conn.cursor()
            cur.execute(sql, (participant_id,socket_id,space))
            # get the generated id back
            #id = cur.fetchone()[0]
            conn.commit()
            cur.close()
            return id
        except:
            raise
        finally:
            self._connection_close(myconn=myconn,shared_conn=conn)

    def update_connection(self, participant_id,socket_id,shared_conn=None):
        """ update a connection. This case not exist. Always is creation and deletion  """
        pass

    def delete_connection_by_participant(self, participant_id,space="PUBLIC",shared_conn=None):
        """ delete all connections by participant. This is used by system to close connections when a logout is requested """

        sql = """delete from client_connections where participant_id =%s and space=%s;"""
        conn = None        
        myconn=False
        deleted_rows=0
  
        try:
            myconn,conn=self._connection_get(shared_conn=shared_conn)            
            cur = conn.cursor()
            cur.execute(sql, (str(participant_id),space,))
            deleted_rows=cur.rowcount
            conn.commit()
            cur.close()            
        except:
            raise
        finally:
            self._connection_close(myconn=myconn,shared_conn=conn)
        return deleted_rows
    
    def _connection_get(self,shared_conn=None):
        
        if shared_conn is not None:
            return True,shared_conn            
        else:
            conn=self.connect()   
            return False,conn 
        
    def _connection_close(self,myconn:bool,shared_conn):
        
        if myconn is True and shared_conn is not None:
            shared_conn.close()
         
        
        

    def delete_connection_by_socket(self, socket_id,shared_conn=None):
        """ delete connection by socket. This is used by socket system """

        sql = """delete from client_connections where socket_id =%s;"""
        conn = None        
        myconn=False
        deleted_rows=0
        
        try:
            myconn,conn=self._connection_get(shared_conn=shared_conn)
            cur = conn.cursor()
            cur.execute(sql, (socket_id,))
            deleted_rows=cur.rowcount
            conn.commit()
            cur.close()
            
        except:
            raise
        finally:
            self._connection_close(myconn=myconn,shared_conn=conn)
        return deleted_rows
        
    def select_connections_by_participant(self, participant_id,space="PUBLIC",shared_conn=None):
        """ select connections by participant.

        Args:
            participant_id (str): id participant
            space (str, optional): space. Defaults to "PUBLIC".
            shared_conn (_type_, optional): shared connection. Defaults to None.

        Raises:
            Exception: Exception

        Returns:
            list: list of connections available for user
        """       
        
        sql = """select participant_id,socket_id from client_connections where participant_id =%s AND space=%s;"""
        conn = None       
        myconn=False
        _rows=0
        connections=[]
        try:
            myconn,conn=self._connection_get(shared_conn=shared_conn)
            cur = conn.cursor()       
            cur.execute(sql, (str(participant_id),str(space)))
            _rows=cur.rowcount
            rows = cur.fetchall()
            for row in rows:
                connection={"participant_id": row[0], "socket_id":row[1]}
                connections.append(connection)
            
            cur.close()
            
        except:            
            raise
        finally:
            self._connection_close(myconn=myconn,shared_conn=conn)
        return connections


    def select_connections_by_space(self, space,shared_conn=None):
        """ select connections by space. """

        sql = """select participant_id,socket_id,connected from client_connections where space =%s;"""
        conn = None        
        myconn=False
        _rows=0
        connections=[]
  
        try:
            myconn,conn=self._connection_get(shared_conn=shared_conn)
            cur = conn.cursor()
            cur.execute(sql, (str(space),))
            _rows=cur.rowcount
            rows = cur.fetchall()
            for row in rows:
                connection={"participant_id": row[0], "socket_id":row[1]}
                connections.append(connection)
            connection={"participant_id": row[0], "socket_id":row[1]}
            cur.close()

        except:
            raise
        finally:
            self._connection_close(myconn=myconn,shared_conn=conn)
        return connection    
    
    def select_connection_by_socket(self, socket_id,shared_conn=None):
        """ select connections by socket_id. """

        sql = """select participant_id,socket_id,connected from client_connections where socket_id =%s;"""
        conn = None        
        myconn=False
        _rows=0
        connection=None
  
        try:
            myconn,conn=self._connection_get(shared_conn=shared_conn)
            cur = conn.cursor()
            cur.execute(sql, (str(socket_id),))
            _rows=cur.rowcount
            row = cur.fetchone()
            connection={"participant_id": row[0], "socket_id":row[1]}
            cur.close()
            
        except:
            raise
        finally:
            self._connection_close(myconn=myconn,shared_conn=conn)
        return connection
    




if __name__ == '__main__':
    from dotenv import load_dotenv
    from pathlib import Path
    
    def test_select_connection_by_socket(socket_id):
        conn=None
        try:
            db=DBHelperPostgress()       
            connection=db.select_connection_by_socket(socket_id=socket_id)
            print (str(connection))
            return True
        except (Exception) as error:
                print(error)
                return False
        finally:
            if conn is not None:
                conn.close()
                print('Database connection closed.')


    def test_delete_connections(participant_id,socket_id):
        conn=None
        try:
            db=DBHelperPostgress()
            db.delete_connection_by_socket(socket_id=socket_id)
            db.delete_connection_by_participant(participant_id=str(participant_id),space="TEST")

            return True
        except (Exception) as error:
                print(error)
                return False
        finally:
            if conn is not None:
                conn.close()
                print('Database connection closed.')

    def test_insert_connections(participant_id,socket_id):
        conn=None
        try:
            db=DBHelperPostgress()           
            id=db.insert_connection(participant_id=str(participant_id),socket_id=socket_id,space="TEST")

            return True
        except (Exception) as error:
                print(error)
                return False
        finally:
            if conn is not None:
                conn.close()
                print('Database connection closed.')

    def test_connection_db():
        conn=None
        try:
            db=DBHelperPostgress()
            conn=db.connect()
            return True
        except (Exception) as error:
            print(error)
            return False    
        finally:
            if conn is not None:
                conn.close()
                print('Database connection closed.')    
                

    def load_env(env_file_name,env_type="DEV",env_folder=".envs") -> None:
        """load environment data for app
        this is stored in user´s home directory as .env.env_file_name.DEV

        Args:
            env_file_name (str): the name of the environment file
            env_name (str, optional): _description_. Defaults to "DEV".
            env_folder (str, optional): _description_. Defaults to ".envs".
        """        
        # Get the user's home directory
        home_dir = Path(os.path.expanduser('~'))
        # Build the path to the environment file (e.g., .env.development or .env.production)
        fname=f'.env.{env_file_name}'
        if env_type:
            fname+="." + env_type
        env_file = home_dir / env_folder / fname

        # Load the environment file
        load_dotenv(dotenv_path=env_file)

    # TESTS
    load_env(env_file_name="apigateway")
    print("Environment vars loaded")
    participant_id=uuid.uuid4()
    socket_id="12345="
    space="TEST"
    print(f"Test connection: {test_connection_db()}") 
    print(f"Test insert_connections: {test_insert_connections(participant_id=participant_id,socket_id=socket_id)}") 
    print(f"Test select_connection_by_socket: {test_select_connection_by_socket(socket_id=socket_id)}") 
    print(f"Test delete_connections: {test_delete_connections( participant_id=participant_id,socket_id=socket_id)}") 
