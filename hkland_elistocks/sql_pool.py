import pymysql
from pymysql.cursors import DictCursor
from DBUtils.PooledDB import PooledDB

# from hkland_component.my_log import logger


class PyMysqlPoolBase(object):
    """
        建立 mysql 连接池的 python 封装
        与直接建立 mysql 连接的不同之处在于连接在完成操作之后不会立即提交关闭
        可复用以提高效率
    """
    _pool = None

    def __init__(self,
                 host,
                 port,
                 user,
                 password,
                 db=None):
        self.db_host = host
        self.db_port = int(port)
        self.user = user
        self.password = str(password)
        self.db = db
        self.connection = self._getConn()
        self.cursor = self.connection.cursor()

    def _getConn(self):
        """
        @summary: 静态方法，从连接池中取出连接
        @return MySQLdb.connection
        """
        if PyMysqlPoolBase._pool is None:
            _pool = PooledDB(creator=pymysql,
                             mincached=1,
                             maxcached=20,
                             host=self.db_host,
                             port=self.db_port,
                             user=self.user,
                             passwd=self.password,
                             db=self.db,
                             use_unicode=True,
                             charset="utf8",
                             cursorclass=DictCursor)
        # print("已经成功从连接池中获取连接")
        return _pool.connection()

    def _exec_sql(self, sql, param=None):
        if param is None:
            count = self.cursor.execute(sql)
        else:
            count = self.cursor.execute(sql, param)
        return count

    def insert(self, sql, params=None):
        """
        @summary: 更新数据表记录
        @param sql: SQL 格式及条件，使用 (%s,%s)
        @param params: 要更新的值: tuple/list
        @return: count 受影响的行数
        """
        return self._exec_sql(sql, params)

    def select_all(self, sql, params=None):
        self.cursor.execute(sql, params)
        results = self.cursor.fetchall()
        return results

    def select_many(self, sql, params=None, size=1):
        self.cursor.execute(sql, params)
        results = self.cursor.fetchmany(size)
        return results

    def select_one(self, sql, params=None):
        self.cursor.execute(sql, params)
        result = self.cursor.fetchone()
        return result

    def insert_many(self, sql, values):
        """
        @summary: 向数据表插入多条记录
        @param sql:要插入的 SQL 格式
        @param values:要插入的记录数据tuple(tuple)/list[list]
        @return: count 受影响的行数
        """
        count = self.cursor.executemany(sql, values)
        return count

    def update(self, sql, param=None):
        """
        @summary: 更新数据表记录
        @param sql: SQL 格式及条件，使用(%s,%s)
        @param param: 要更新的  值 tuple/list
        @return: count 受影响的行数
        """
        return self._exec_sql(sql, param)

    def delete(self, sql, param=None):
        """
        @summary: 删除数据表记录
        @param sql: SQL 格式及条件，使用(%s,%s)
        @param param: 要删除的条件 值 tuple/list
        @return: count 受影响的行数
        """
        return self._exec_sql(sql, param)

    def begin(self):
        """
        @summary: 开启事务
        """
        self.connection.autocommit(0)

    def end(self, option='commit'):
        """
        @summary: 结束事务
        """
        if option == 'commit':
            self.connection.commit()
        else:
            self.connection.rollback()

    def dispose(self, isEnd=1):
        """
        @summary: 释放连接池资源
        """
        if isEnd == 1:
            self.end('commit')
        else:
            self.end('rollback')
        self.cursor.close()
        self.connection.close()
