import datetime
import json
import os
import time

import pymysql

from DBUtils.PooledDB import PooledDB
from httprunner.util.parserConf import ParserConf


def singleton(cls, *args, **kw):
    instances = {}
    def _singleton(*args,**kwargs):
        data = kwargs.get('database','DATABASE')
        if data not in instances :
            instances[data] = cls(*args, **kwargs)
        # database.append(data)
        return instances[data]
    return _singleton

@singleton
class DB_CONN(object):
    def __init__(self,**kwargs):
        parse = ParserConf(os.environ['DATA_PATH'])
        database = kwargs.get('database','DATABASE')
        ip = parse.get_config_value_by_key(database, "ip")
        port = parse.get_config_value_by_key(database, "port")
        user = parse.get_config_value_by_key(database, "user")
        password = parse.get_config_value_by_key(database, "password")
        charset = parse.get_config_value_by_key(database, "charset")
        try:
            self.__pool = PooledDB(creator=pymysql,
                                   maxusage=None,
                                   maxconnections=10,
                                   mincached=5,
                                   maxcached=10,
                                   maxshared=10,
                                   blocking=True,
                                   host=ip,
                                   port=int(port),
                                   user=user,
                                   passwd=password,
                                   charset=charset)
        except Exception:
            print('数据库连接失败')


    def db_query_count(self,sql):
        conn = self.__pool.connection()
        cur = conn.cursor(cursor=pymysql.cursors.DictCursor)
        try:
            cur.execute(sql)
            conn.commit()
            return cur
        except Exception as e:
            print('数据查询失败', e)
        finally:
            cur.close()
            conn.close()

    def db_Query_Json(self, sql):
        '''
        获取数据json格式游标，使用需要fetchall()或fetchone()fetchmany()
        :param sql: 查询语句
        :return: 游标json格式 使用时需要使用fetchall()或fetchone()fetchmaeeny()
        '''
        conn = self.__pool.connection()
        cur = conn.cursor(cursor=pymysql.cursors.DictCursor)
        len = 0
        try:
            if len == 0:
                for i in range(5):
                    len = cur.execute(sql)
                    if len > 0:
                        conn.commit()
                        return cur
                    time.sleep(1)
            return cur
        except Exception as e:
            print('数据查询失败',e)
        finally:
            cur.close()
            conn.close()

    #
    def db_Query_tuple(self, sql, params=None):
        '''
        获取数据元组格式游标，使用需要fetchall()或fetchone()fetchmany()
        :param sql: 查询语句
        :return: 元组格式游标，使用需要fetchall()或fetchone()fetchmany()
        '''
        #self.conn = DB_CONN.__pool.connection()
        conn = self.__pool.connection()
        cur = conn.cursor()
        try:
            if params:
                cur.execute(sql, params)
            else:
                cur.execute(sql)
            return cur
        except Exception as e:
            print('数据库查询失败')
        finally:
            cur.close()
            # self.conn.close()
            conn.close()

    # 数据库插入
    def db_Insert(self, sql, params):
        '''
        数据库插入
        :param sql: 插入语句
        :param params: 插入数据
        :return: 插入成功数目
        '''
        #self.conn = DB_CONN.__pool.connection()
        #conn = self.__pool.connection()
        cur = self.conn.cursor()
        try:
            data_counts = cur.execute(sql, params)
            self.conn.commit()
            return data_counts
        except Exception as e:
            self.conn.rollback()
        finally:
            cur.close()
            # self.conn.close()
            self.conn.close()

    # 数据库更新
    def db_Update(self, sql, params=None):
        '''
        :param sql:
        :return:
        '''
        #self.conn = DB_CONN.__pool.connection()
        #conn = self.__pool.connection()
        cur = self.conn.cursor()
        try:
            if params:
                data_counts = cur.execute(sql, params)
            else:
                data_counts = cur.execute(sql)
            self.conn.commit()
            return data_counts
        except Exception as e:
            self.conn.rollback()
        finally:
            cur.close()
            # self.conn.close()
            self.conn.close()

    def db_Batch(self, sql, params):

        #self.conn = DB_CONN.__pool.connection()
        #conn = self.__pool.connection()
        cur = self.conn.cursor()
        try:
            data_counts = cur.executemany(sql, params)
            self.conn.commit()
            return data_counts
        except Exception as e:
            self.conn.rollback()
            return False, '***执行更新失败，请检查数据！错误信息：%s' % e + "查询语句为：" + sql
        finally:
            cur.close()
            # self.conn.close()
            self.conn.close()


# 数据库中时间转换json格式  在返回的json方法里加上cls=MyEncoder
class MyEncoder(json.JSONEncoder):
    def default(self, obj):
        '''
        针对datetime格式的转换
        :param obj: 参数数据
        :return: 返回json格式
        '''
        try:
            # if isinstance(obj, datetime.datetime):
            #     return int(mktime(obj.timetuple()))
            if isinstance(obj, datetime):
                return obj.strftime('%Y-%m-%d %H:%M:%S')
            elif isinstance(obj, datetime.date):
                return obj.strftime('%Y-%m-%d')
            else:
                return json.JSONEncoder.default(self, obj)
        except Exception as e:
            return False


# 数据库数据直接转换成json格式输出 无数据 返回FALSE
def getJsonFromDatabase(sql):
    cur = DB_CONN().db_Query_Json(sql)
    if cur is None:
        return False
    else:
        return cur.fetchall()


def getTupleFromDatabase(sql):
    cur = DB_CONN().db_Query_tuple(sql)
    if cur.rowcount == 0:
        return False
    else:
        return cur.fetchall()


def insertToDatabase(table, data, **kwargs):
    '''

    :param table: 表名
    :param data: 插入数据
    :return: 插入成功数
    '''
    col_list = dict()
    col_list.update(data)
    col_list.update(kwargs)
    #table_data = {k: v for k, v in col_list.items() if v}
    table_data = {}
    for k, v in col_list.items():
        if v:
            if isinstance(v, dict):
                v = json.dumps(v, ensure_ascii=False)
            elif not isinstance(v, str):
                v = str(v)

            table_data[k] = v
    key = ",".join(table_data.keys())
    value = tuple(table_data.values())
    sql = 'INSERT INTO ' + table + ' ( ' + key + ' ) VALUES %s'
    result = DB_CONN().db_Update(sql, (value,))

    return result


def updateToDatabase(table, data, **kwargs):
    '''

    :param table:表名
    :param data: 更新数据
    :param col: 定位
    :param val:定位值
    :return: 更新成功数
    '''
    table_data = {}
    for k, v in data.items():
        if v:
            if isinstance(v, dict):
                v = json.dumps(v, ensure_ascii=False)
            elif not isinstance(v, str):
                v = str(v)
            table_data[k] = v
    col_lists = tuple(table_data.keys())
    col_values = tuple(table_data.values())
    setvalue = '=%s,'.join(col_lists) + '=%s'

    wherekey = tuple(kwargs.keys())
    where_value = tuple(kwargs.values())
    wherevalue = '=%s AND '.join(wherekey) + '=%s'
    sql = "UPDATE " + table + ' SET ' + setvalue + ' WHERE ' + wherevalue
    params = col_values + where_value
    result = DB_CONN().db_Update(sql, params)

    return result


def searchToDatabase(table, data):
    '''
    生成like语句
    :param data:
    :return:
    '''
    col = ''
    for i in data.keys():
        key = i
        val = data[key]
        col = col + key + ' like "%' + val + '%" ' + ' and '
    return col