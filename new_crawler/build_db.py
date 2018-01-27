import db
import json

def process_file(in_path):
    f = open(in_path)

    for line in f:
        line.strip()


if __name__ == '__main__':

    in_path = sys.argv[1]
    db_path = sys.argv[1]
