import os

from httprunner.util.runnercase import ownerTest

if __name__=='__main__':
    os.environ['TEST_ENV']='TEST1'
    runtest=ownerTest(log_level='WARNING')
    runtest.runtestcase(test_path='testcases/order_cases.yml',report_title='接口测试报告')
