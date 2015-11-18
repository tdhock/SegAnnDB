from plotter.db import UserModel
import time

while 1:
    for u in UserModel.db_keys():
         res = UserModel(u)
         res.learn()
    time.sleep(1)
