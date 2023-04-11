import unittest
import os

from scheme import Universal


class TestUniversal(unittest.TestCase):
    def test_insertion_path(self):
        scheme = Universal(gamma=2)
        secret_key = 123
        recipient = 0
        data = '../../datasets/german_credit_sample.csv'
        fingerprinted = scheme.insertion(data, recipient, secret_key)
        # suspect = scheme.detection(fingerprinted, secret_key)
        self.assertIsNotNone(fingerprinted)

    def test_insert_and_save(self):
        scheme = Universal(gamma=2)
        secret_key = 123
        recipient = 0
        data = '../../datasets/german_credit_sample.csv'
        fingerprinted = scheme.insertion(data, recipient, secret_key, save=True)
        # suspect = scheme.detection(fingerprinted, secret_key)
        self.assertIsNotNone(fingerprinted)

    def test_detection_path(self):
        scheme = Universal(gamma=2, fingerprint_bit_length=8)
        secret_key = 123
        recipient = 0
        data = '../../datasets/german_credit_sample.csv'
        fingerprinted = scheme.insertion(data, recipient, secret_key)
        suspect = scheme.detection(fingerprinted, secret_key)
        self.assertEqual(recipient, suspect)

    def test_detection_2(self):
        scheme = Universal(gamma=2)
        secret_key = 123
        recipient = 0
        data = '../../datasets/adult.csv'
        fingerprinted = scheme.insertion(data, recipient, secret_key)
        suspect = scheme.detection(fingerprinted, secret_key)
        self.assertEqual(recipient, suspect)

    def test_insert_and_save_custom(self):
        scheme = Universal(gamma=2)
        secret_key = 123
        recipient = 0
        data = '../../datasets/german_credit_sample.csv'
        outfile = "fingerprinted/gc.csv"
        scheme.insertion(data, recipient, secret_key, write_to=outfile)
        self.assertTrue(os.path.isfile(outfile))
        os.remove(outfile)

    def test_decimal_data(self):
        scheme = Universal(gamma=2)
        secret_key = 123
        recipient = 0
        data = '../../datasets/abalone_data.csv'
        outfile = "fingerprinted/abalone.csv"
        scheme.insertion(data, recipient, secret_key, write_to=outfile)
        self.assertTrue(os.path.isfile(outfile))

    def test_numerical_data(self):
        scheme = Universal(gamma=2)
        secret_key = 123
        recipient = 0
        data = '../../datasets/breast_cancer_wisconsin.csv'
        outfile = "fingerprinted/breast_cancer_wisconsin.csv"
        scheme.insertion(data, recipient, secret_key, write_to=outfile)
        self.assertTrue(os.path.isfile(outfile))

    def test_decimal_detection(self):
        scheme = Universal(gamma=2, fingerprint_bit_length=128)
        secret_key = 123
        recipient = 0
        data = '../../datasets/abalone_data.csv'
        fp_data = scheme.insertion(data, recipient, secret_key)
        suspect = scheme.detection(fp_data, secret_key)
        self.assertEqual(suspect, recipient)

    def test_decimal_detection_2(self):
        scheme = Universal(gamma=2, fingerprint_bit_length=32)
        secret_key = 123
        recipient = 0
        data = '../../datasets/insurance.csv'
        fp_data = scheme.insertion(data, recipient, secret_key)
        suspect = scheme.detection(fp_data, secret_key)
        self.assertEqual(suspect, recipient)

    def test_subset_decimal(self):
        scheme = Universal(gamma=5, fingerprint_bit_length=8)
        secret_key = 123
        recipient = 0
        data = '../../datasets/insurance.csv'
        fp_data = scheme.insertion(data, recipient, secret_key, include=['bmi', 'age', 'charges'])
        suspect = scheme.detection(fp_data, secret_key, include=['bmi', 'age', 'charges'])
        self.assertEqual(suspect, recipient)

    def test_insurance_default(self):
        scheme = Universal(gamma=1)
        secret_key = 123
        recipient = 0
        data = '../../datasets/insurance.csv'
        fp_data = scheme.insertion(data, recipient, secret_key)
        suspect = scheme.detection(fp_data, secret_key)
        self.assertEqual(suspect, recipient)

    def test_insurance(self):
        scheme = Universal(gamma=10, fingerprint_bit_length=16)
        secret_key = 1234
        recipient = 0
        data = '../../datasets/insurance.csv'
        fp_data = scheme.insertion(data, recipient, secret_key, write_to='fingerprinted/insurance.csv')

        suspect = scheme.detection(fp_data, secret_key)
        self.assertEqual(suspect, recipient)

    def test_bank_personal_loan_modelling(self):
        scheme = Universal(gamma=10, fingerprint_bit_length=16)
        secret_key = 1234
        recipient = 0
        data = '../../datasets/Bank_Personal_Loan_Modelling.csv'
        fp_data = scheme.insertion(data, recipient, secret_key)

        suspect = scheme.detection(fp_data, secret_key)
        self.assertEqual(suspect, recipient)
