
class DBHelper:
    """
    Class to manage socket connections for users
    """

    def __init__(self,connection_data:dict=None):
        raise NotImplementedError    
            
    def _load_ddbb_config(self):
        raise NotImplementedError                          

    def connect(self):
        """ Connect to the database server . Primarily to postgress"""
        raise NotImplementedError


    def insert_connection(self, participant_id,socket_id,space="PUBLIC",shared_conn=None):
        """ insert a new connection  """
        raise NotImplementedError

    def update_connection(self, participant_id,socket_id,shared_conn=None):
        """ update a connection. This case not exist. Always is creation and deletion  """
        raise NotImplementedError

    def delete_connection_by_participant(self, participant_id,space="PUBLIC",shared_conn=None):
        """ delete all connections by participant. This is used by system to close connections when a logout is requested """
        raise NotImplementedError
    
    def _connection_get(self,shared_conn=None):
        raise NotImplementedError
        
    def _connection_close(self,myconn:bool,shared_conn):
        raise NotImplementedError
         
        
        

    def delete_connection_by_socket(self, socket_id,shared_conn=None):
        """ delete connection by socket. This is used by socket system """
        raise NotImplementedError
        
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
        raise NotImplementedError


    def select_connections_by_space(self, space,shared_conn=None):
        """ select connections by space. """
        raise NotImplementedError  
    
    def select_connection_by_socket(self, socket_id,shared_conn=None):
        """ select connections by socket_id. """
        raise NotImplementedError
    






