from pathlib import Path

def runApp():
    myfile = Path('mylechero.txt')
    myfile.touch(exist_ok=True)
    f = open(myfile)