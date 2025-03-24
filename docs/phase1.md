# Phase 1: Break the fingerprint
You were entrusted with a fingerprinted dataset from a bank _Super Bank Alliance_. This dataset holds valuable insights into the financial habits of its clients and is used to predict loans.
However, you have decided to go rogue :smiling_imp:. You want to redistribute the dataset while ensuring that the original owner cannot prove it came from your copy. Your challenge? Manipulate the dataset to disrupt the fingerprint while keeping the data useful. If you render the dataset useless, no one will trust your source, and your grand scheme will crumble. You are certain that the fingerprint is embedded in the data, however, without the bank’s secret key, you cannot certainly know where the marks are. 
>So the challenge is: How to attack the fingerprinted dataset in a way that breaks the fingerprint without destroying data credibility?

## Key points:
- :chart_with_upwards_trend: Keep It Useful: Choose utility metrics that ensure the dataset remains functional for predicting loan defaults. These metrics should remain high after your modifications. 
- :hammer_and_wrench: Choose Your Strategy: You can apply any attack method—noise injection, shuffling, feature transformations, data augmentations, assumptions or knowledge about the embedding algorithm, or even completely unconventional approaches.
- :heavy_check_mark: Submit Your Attacked Dataset(s): You are free to submit multiple versions if you have different ideas on how to break the fingerprint.
- :writing_hand: Explain Your Process: In a detailed report, describe:
  - Your thought process and reasoning.
  - The steps you took to manipulate the dataset.
  - Any utility tests you performed (including the code if applicable).
  - The expected results
  - **Reproducibility—your modifications should be replicable!**

## Questions:
After you are done attacking, answer the following questions:
1. How obvious do you think the fingerprint was before you started attacking it? (0-10)
2. How confident are you that you broke the fingerprint? (0-10)
3. How difficult did you find the task of disrupting the fingerprint? (0-10)
4. Why do you believe your attack was effective (or not)?
5. If you had more time, what would you do differently?
6. Did you notice any patterns in the data that gave you hints about the fingerprinting method?
7. What was your biggest challenge in balancing fingerprint disruption and data utility?

## Submission:
- documentation not exceeding 2 pages 
- code if applicable
- attacked dataset(s) in .csv 

See full submission details [here](submission.md).
