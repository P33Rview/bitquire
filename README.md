<div align="center">

  <img src="https://img.shields.io/badge/Python-3.14-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Pandas-Data_Analysis-150458?style=for-the-badge&logo=pandas&logoColor=white" alt="Pandas">
  <img src="https://img.shields.io/badge/Supabase-Database-3FCF8E?style=for-the-badge&logo=supabase&logoColor=white" alt="Supabase">
  <img src="https://img.shields.io/badge/GitHub_Actions-Automation-2088FF?style=for-the-badge&logo=githubactions&logoColor=white" alt="GitHub Actions">

</div>

# bitquire (Automated Bitcoin Investing)
₿ Bitcoin · ⚡ Automated · 📅 Weekly

A lightweight automation tool for systematic Bitcoin Dollar-Cost Averaging (DCA), powered by GitHub Actions and Supabase.
> Allows the user to set a lower and upper thresholds of weekly contributions, which is calculated by linear extrapolation based on the **BTC 200 weekly moving average** and Fear and Greed index weighting.



<img width="796" height="575" alt="image" src="https://github.com/user-attachments/assets/2893235f-9df0-4581-b036-45d721a62cdd" />


## ✨ Overview

BTC Weekly DCA automates Bitcoin Dollar-Cost Averaging calculations, providing a consistent, hands-off approach to supporting a long-term investment strategy.

The Python script runs automatically every Monday via GitHub Actions, with Supabase integration for database operations. Currently, the solution is semi-automatic. An email notification is sent with the exact amount to buy the BTC:

<img width="525" height="609" alt="image" src="https://github.com/user-attachments/assets/f771f326-3cb2-4de6-bb39-4992e81f5faa" />



**Stay consistent. Automate the routine. ₿**

## Proposed future improvements

The first priority is to do the whole process fully automatic, but I need to figure a way to access the internet banking account programatically. Subsequently, I am planning on adding a UI, that would allow to track the current return. Finally, this would all be displayed in a compact mobile app accessible through Apple Store.
