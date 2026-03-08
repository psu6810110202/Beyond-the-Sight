import unittest
import sys
import os

if __name__ == '__main__':
    # Add project root to sys path so modules can be imported
    sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
    
    # Discover and run all tests in the tests/ directory
    loader = unittest.TestLoader()
    suite = loader.discover('.', pattern='test_*.py')
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    if result.wasSuccessful():
        print("\nAll tests passed! Ready for production.")
        sys.exit(0)
    else:
        print("\nSome tests failed. Please review the output above.")
        sys.exit(1)
