from plotter.db import ProfileQueue

while 1:
    ProfileQueue.process_one()
    
