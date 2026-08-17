"""850 SCOS Portal — entry point."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from api.server import main
if __name__ == '__main__': main()
