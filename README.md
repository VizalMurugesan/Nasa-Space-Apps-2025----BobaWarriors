# 🌾 SMARTFarming  
**Simulated Management of Agricultural Resources and Terrain for Farming**

---

### Overview  
**SMARTFarming** is an **interactive crop management simulator** that combines real-world **soil** and **weather data** with **user-driven farming decisions**. Through an intuitive interface, users can:  
- Select a location on the world map.  
- Choose a start date for farming.  
- Manage crops using realistic soil and weather conditions.  
- Make decisions on ploughing, sowing, watering, and fertilizing.  

The simulation dynamically responds to player actions, showing changes in **soil moisture**, **fertility**, and **predicted yield** in real time. While the system is designed for **global scalability**, this hackathon prototype focuses on a **single region** for feasibility.  

---

## 🚀 Features  
- 🌍 **Real-world data integration** via NASA POWER (weather) and WOFOST (soil).  
- 🌾 **Dynamic crop simulation** using the **Python Crop Simulation Environment (PCSE)**.  
- 🧑‍🌾 **Interactive management tools** — plough, sow, water, and fertilize your fields.  
- 📊 **Live feedback system** with soil moisture, fertility, and yield indicators.  
- 🕹️ **Time controls** for adjusting simulation speed and observing crop growth cycles.  

---

## 🧩 Tech Stack  

| Component | Technology |
|------------|-------------|
| **Game Engine** | Unity |
| **Frontend Language** | C# (via Unity) |
| **Backend Server** | Python |
| **Weather Data** | [NASA POWER Daily API](https://power.larc.nasa.gov/) |
| **Soil Data** | WOrld FOod STudies (WOFOST) |
| **Crop Model** | Python Crop Simulation Environment ([PCSE](https://pcse.readthedocs.io/)) |

---

## 🛠️ Development Environments  
| Purpose | Recommended Tool |
|----------|------------------|
| **Unity Development** | Unity Hub + Editor |
| **C# Scripting** | Visual Studio |
| **Python Server** | Visual Studio Code |

---

## ⚙️ Setup Instructions  

### 1️⃣ Clone the Repository  
```bash
git clone https://github.com/VizalMurugesan/Nasa-Space-Apps-2025----BobaWarriors.git
cd Nasa-Space-Apps-2025----BobaWarriors
```

---

### 2️⃣ Python Environment Setup  

1. **Create a virtual environment (optional but recommended):**  
   ```bash
   python -m venv venv
   source venv/bin/activate       # macOS/Linux
   venv\Scripts\activate          # Windows
   ```

2. **Install required dependencies:**  
   ```bash
   pip install pcse pandas matplotlib requests
   ```

3. **Run the Python server (`game.py`):**  
   ```bash
   python game.py
   ```
   This script initializes a local data server that Unity communicates with for fetching weather and soil data.  
   - By default, it runs on `http://localhost:5000`.  
   - Ensure the terminal stays open while Unity is running.  
   - If you change the port, update the corresponding Unity connection URL in the project’s scripts.

   ✅ **Expected output when running correctly:**  
   ```
   * Serving Flask app 'game'
   * Running on http://127.0.0.1:5000
   ```

---

### 3️⃣ Unity Setup  

1. **Launch Unity Hub** and click **Add Project**.  
2. Select the cloned folder and open it in Unity.  
3. Allow Unity to automatically import assets and dependencies (this may take a few minutes).  
4. Once the project loads, click **▶ Play** in the Unity Editor to start the simulation.  

---

## 🕹️ How to Play  

1. **Select a Location:**  
   Begin on a world map where you can click any location to start.  

2. **Choose a Start Date:**  
   Pick the month and date to begin your farming season.  

3. **Simulate and Manage:**  
   Your farm scene appears with soil and weather data from the chosen location.  
   Use the available tools:  
   - **Plough** – prepare the soil.  
   - **Sow** – plant seeds.  
   - **Water** – increase soil moisture.  
   - **Fertilize** – boost soil fertility and yield.  

4. **Monitor Crop Stats:**  
   Watch the three bars at the top:  
   - **Soil Moisture** 🌧️  
   - **Soil Fertility** 🌿  
   - **Predicted Yield** 🌾  

5. **Control Time:**  
   - ⏫ **Speed Up** – advance days quickly.  
   - ⏬ **Slow Down** – observe crop growth in detail.  

6. **End of Simulation:**  
   When the crop matures, results display yield outcomes and lessons learned.  

---

## 🧑‍💻 Authors  

| Name | Email |
|------|--------|
| **Daiwik Bhola** | [daiwik.bhola@gmail.com](mailto:daiwik.bhola@gmail.com) |
| **Kenneth Renald Hoesien** | [KennethRenald@gmail.com](mailto:KennethRenald@gmail.com) |
| **Shubham Verma** | [vermashubham1980@gmail.com](mailto:vermashubham1980@gmail.com) |
| **Vizal Murugesan** | [vizal.rmurugesan@gmail.com](mailto:vizal.rmurugesan@gmail.com) |

---

## 🌟 Acknowledgements  
This project was developed as part of **NASA Space Apps 2025 – Team BobaWarriors**.  
Special thanks to **NASA POWER**, **WOFOST**, and the **PCSE** developers for open-access data and tools enabling this simulation.  
