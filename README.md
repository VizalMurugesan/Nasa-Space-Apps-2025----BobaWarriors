**Project Title**

SmartFarming

**Description**

Smartfarming is an interactive crop management simulator that combines real-world soil and weather data with user-driven farming decisions. Through its interface, users can choose crops, set management strategies, and watch their simulations progress under realistic conditions. While Smartfarming is designed to be globally applicable, the current hackathon version focuses on one specific location for feasibility.

**Getting Started**

Development Software- Unity

C# environment - Visual Studio Recommended

Python environment- Visual Studio Code Recommended

Weather Dataset- NASA POWER Daily API –

Soil Dataset- WOrld FOod STudies (WOFOST)

Model- Python Crop Simulation Environment (PCSE)

**Setting up the environment-**

1. Clone the repository from Github- [VizalMurugesan/Nasa-Space-Apps-2025----BobaWarriors](https://github.com/VizalMurugesan/Nasa-Space-Apps-2025----BobaWarriors/tree/main)
2. Install Required Python Packages

Open a terminal or command prompt and run:

**pip install pcse pandas matplotlib requests**

1. Retrieve weather data using the NASA POWER Daily API, which provides real-time weather parameters (such as temperature, rainfall, and humidity) for any given location.
   API endpoint:
   <https://power.larc.nasa.gov/api/temporal/daily/point>
2. Open the project in Visual Studio Code for the Python scripts and Visual Studio for the Unity C# components.
3. Launch Unity Hub, add the cloned project folder, and open it in Unity. Allow Unity to automatically import assets and dependencies (this may take a few minutes).
4. Once loaded, click Play in the Unity Editor to run the simulation. Ensure your Python model connection placeholder is set up for future integration of live weather and soil data updates.

**Guide to Use the SmartFarming-**

* When you open the project, you’re greeted with a world map where you can click on any location to begin your simulation.
* After choosing a location, select the month and date when you want to begin your farming journey.
* Once selected, a mockup farm appears, displaying actual soil data and weather conditions from your chosen location.
* You’ll have access to four farming tools plough, sow, water, and fertilizer. Start by ploughing the land, sow the seeds to begin crop growth, and then use water and fertilizer to maintain and improve your crops.
* Three bars at the top display soil moisture, soil fertility, and predicted yield. These values dynamically change based on your actions for example, watering increases moisture, while fertilizing improves fertility and yield.
* Two buttons allow you to control time: the upward button speeds up the simulation, increasing the day counter as time progresses, while the downward button slows it down for closer observation of crop growth.
* The simulation ends when the crop reaches maturity, showing yield outcomes and lesson.

**Authors**

**Daiwik Bhola –** **daiwik.bhola@gmail.com**

**Kenneth Renald Hoesien-** **KennethRenald.Hoesie@mytwu.ca**

**Shubham Verma-** **vermashubham1980@gmail.com**

**Vizal Murugesan-** **vizal.rmurugesan@gmail.com**
