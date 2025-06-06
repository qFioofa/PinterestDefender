import os
import argparse
from pDataBase import pDataBase
from pServer import pServer, appWrapper


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--debug', '--d', action='store_true',
                        help='Enable debug mode (default: False)')

    args, unknown = parser.parse_known_args()

    os.makedirs("static/uploads", exist_ok=True)
    os.makedirs("database", exist_ok=True)

    appWrapper.init()
    pDataBase(pServer.get_app())
    pServer.run(debug=args.debug)