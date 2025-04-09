# Phase 2: Collusion attack

In the previous phase, you worked alone, trying to manipulate your fingerprinted dataset to erase any traceable signatures. But now, the game has changed. 
Your trusted collaborator Bob has secretly shared their fingerprinted copy with you. 
This means you now have **two different versions** of the dataset — one with your signature, and one with Bob’s (_disclaimer_: among your fellow students, there might be someone else who has a different copy from you and Bob). 
With multiple versions of the dataset in play, you can compare different datasets and use the discrepancies to your advantage. 
However, beware — if you recklessly merge or modify the datasets, you might expose yourself and Bob instead of erasing your tracks!
>Armed with multiple fingerprinted datasets, can you remove the fingerprint and hide all collaborators' identities?

## Key Points
Armed with two or more datasets, you can now:
- :detective: Detect Differences: Examine the variations between your copy and Bob’s. What patterns emerge? Are certain features differently modified? Does the structure give you hints about the fingerprinting method?
- :hammer_and_wrench: Leverage Multiple Copies: You can average, blend, or selectively replace values between datasets…
- :chart_with_upwards_trend: Keep utility in mind: Similarly to the previous phase, you shall keep the utility of your resulting dataset high. 
- :heavy_check_mark: Submit Your Attacked Dataset(s): You are free to submit multiple versions if you have different ideas on how to break the fingerprint.
- :writing_hand: Explain Your Process: In a detailed report, describe:
  - Your thought process and reasoning.
  - The steps you took to manipulate the dataset.
  - Any utility tests you performed (including the code if applicable).
  - The expected results
  - **Reproducibility—your modifications should be replicable!**


## Questions
After you are done attacking, answer the following questions: 
1. Having multiple datasets, how obvious do you think the fingerprint was before you started attacking it? (0-10)
2. How eager were you to include Bob’s copy to design your attack? (0-10)
3. How eager were you to include more copies to design your attack? (0-10)
4. How confident are you that you broke the fingerprint and that no collaborator can be detected? (0-10)
5. How confident are you that at least one collaborator cannot be detected? (0-10)
6. How difficult did you find the task of disrupting the fingerprint? (0-10)
7. How many collaborators (including Bob) did you work with? (Answer truthfully, there is no wrong answer here)
8. Why do you believe your attack was effective (or not)?
9. If you had more time, what would you do differently?
10. Did you notice any patterns in the data or in the dataset differences that gave you hints about the fingerprinting method?
11. What was your biggest challenge in balancing fingerprint disruption and data utility?
12. How does having multiple datasets help or complicate your attack?

## Submission
- documentation not exceeding 4 pages (even in case of collaborations, please each submit your own report)
- code (scripts and corresponding output, e.g. a Jupyter notebook with the results of the run(s), or otherwise saving the CLI output to a .txt file)
- attacked dataset(s), each in a separate .csv following the same structure as the original file

See full submission details [here](submission.md).
