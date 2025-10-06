using NUnit.Framework;
using System;
using System.Collections.Generic;
using TMPro;
using UnityEngine;

public class GameManager : MonoBehaviour
{
    public static GameManager Instance { get; private set; }
    float TotalTime;
    float phaseTime;



    [SerializeField] float Phase0Duration;
    [SerializeField] float Phase1Duration;
    [SerializeField] float Phase2Duration;
    [SerializeField] float Phase3Duration;
    public TimeManager timeManager;
    public DateMonthChoiceManager dateandtimeselectmanager;
    public PythonUnityConnector connector;

    public enum Area { polar, Temperate, tropical, Equitorial}

    public enum Phase {None, one, two, three }
    [SerializeField] Phase phase = Phase.one;
    public List<GameObject> Farms;

    public int SowDay;
    public int SowMonth;

    public float currentTemp;
    public TextMeshProUGUI TemperatureText;

    //booleans
    public bool HasChosenMap;
    public bool HasChosenDate;
    public bool HasPloughed;
    public bool HasSownSeed;

    public enum IrrigationType { None, high, drip}
    public IrrigationType irrigationtype;
    public GameObject irrigationPanel;

    public GameObject worldmap;

    public ParticleSystem rain;
    public ParticleSystem snow;

    public UIBar NitrogenBar;
    public UIBar YieldBar;
    public UIBar MoistureBar;

    public TextMeshProUGUI MessageText;

    private void Awake()
    {
        if (Instance != null && Instance != this)
        {
            Destroy(gameObject);
            return;
        }
        Instance = this;
        Seed seed = GetComponent<Seed>();
        foreach(var farm in Farms)
        {
            farm.GetComponent<Farm>().SetPlotSprites(seed.phase1sprite, seed.phase2sprite, seed.phase3sprite);
        }
        timeManager = GetComponent<TimeManager>();
        connector = GetComponent<PythonUnityConnector>();
    }

    private void Update()
    {
        if (HasChosenDate && HasChosenMap&& HasPloughed && HasSownSeed)
        {
            if(phase == Phase.None && phaseTime> Phase0Duration)
            {
                ChangeAllFarmsToPhase1();
            }
            if (phase == Phase.one && phaseTime > Phase1Duration)
            {
                ChangeAllFarmsToPhase2();
            }
            if (phase == Phase.two && phaseTime > Phase2Duration)
            {
                ChangeAllFarmsToPhase3();
            }


            TotalTime += Time.deltaTime;
            phaseTime += Time.deltaTime;
        }
        
        
    }

    void ChangeAllFarmsToPhase2()
    {
        foreach (var farm in Farms)
        {
            farm.GetComponent<Farm>().ChangeAllPlotToPhase2();

        }
        phase = Phase.two;
        phaseTime = 0f;
        ShowMessageText("seeds of hardwork");
    }

    void ChangeAllFarmsToPhase3()
    {
        foreach (var farm in Farms)
        {
            farm.GetComponent<Farm>().ChangeAllPlotToPhase3();

        }
        phase = Phase.three;
        phaseTime = 0f;

        ShowMessageText("aha! the fields! the beutiful plants");
    }

    void ChangeAllFarmsToPhase1()
    {
        foreach (var farm in Farms)
        {
            farm.GetComponent<Farm>().ChangeAllPlotToPhase1();

        }
        phase = Phase.one;
        phaseTime = 0f;

        ShowMessageText("aha! the fields!");
    }

    public void SetAreaPolar()
    {
        //Debug.Log("polar");
    }

    public void SetAreaTemperate()
    {
        //Debug.Log("Temperate");
    }
    public void SetAreaTropical()
    {
        //Debug.Log("Tropical");
    }

    public void SetAreaEquitorial()
    {
        //Debug.Log("Equitorial");

    }

    public void CheckForArea(Vector2 pos)
    {
        float x = pos.x;
        float screenWidth = Screen.width;
        // Divide screen into 4 equal vertical zones:
        if (x < screenWidth * 0.25f)
        {
            SetAreaPolar();
        }
        else if (x < screenWidth * 0.5f)
        {
            SetAreaTemperate();
        }
        else if (x < screenWidth * 0.75f)
        {
            SetAreaTropical();
        }
    }

    public string GetSownDate()
    {
        return "" + SowDay + "." + SowMonth;
    }

    public void SetTemperature(float value)
    {
        currentTemp = value;
        float rounded = Mathf.Round(currentTemp * 10f) / 10f;
        TemperatureText.text = "Temp: " + rounded+ " C";

    }

    public void SetIrrigationTypeToNone()
    {
        irrigationtype = IrrigationType.None;
        irrigationPanel.SetActive(false);
        continueGame();

    }

    public void SetIrrigationTypeToDrip()
    {
        irrigationtype = IrrigationType.drip;
        irrigationPanel.SetActive(false);
        continueGame();

    }
    public void SetIrrigationTypeToHigh()
    {
        irrigationtype = IrrigationType.high;
        irrigationPanel.SetActive(false);
        continueGame();

    }

    public void OpenIrrigationPanel()
    {
        irrigationPanel.SetActive(true);
        StopGame();
    }

    public void Plough()
    {
        HasPloughed = true;
        foreach(var farm in Farms)
        {
            foreach(var plot in farm.GetComponent<Farm>().farmPlots)
            {
                plot.transform.GetChild(0).gameObject.SetActive(true);
            }
        }

    }

    public void SowSeed()
    {
        if (HasPloughed)
        {
            HasSownSeed = true;
            Time.timeScale = 1f;
        }
        else
        {
            SendMessage("TO SowSeed remember to till SetWeather land first!");
        }
        
    }

    public void ClickOnWorldmap()
    {
        
        HasChosenMap = true;
        dateandtimeselectmanager.gameObject.SetActive(true);

    }

    public void StopGame()
    {
        Time.timeScale = 0f;
    }

    public void continueGame()
    {
        Time.timeScale = timeManager.GameSpeed;
    }

    internal bool UnlockedAllInitialFeatures()
    {
        return HasChosenMap && HasChosenDate && HasPloughed && HasSownSeed;
    }

    public void SetBarValues(float NitrogenVal, float moistureVal, float yieldVal)
    {
        NitrogenVal *= 1000f;
        NitrogenVal = MathF.Round(NitrogenVal);

        moistureVal *= 100000f;
        moistureVal = MathF.Round(moistureVal);
        moistureVal /= 100f;

        NitrogenBar.ChangeValue(NitrogenVal);
        MoistureBar.ChangeValue(moistureVal);
        YieldBar.ChangeValue(yieldVal);
    }

    public void SetWeatherToSunny()
    {
        snow.gameObject.SetActive(false);
        rain.gameObject.SetActive(false);
    }

    public void SetWeatherToRainy()
    {
        snow.gameObject.SetActive(false);
        rain.gameObject.SetActive(true);
    }

    public void SetWeatherToSnow()
    {
        snow.gameObject.SetActive(true);
        rain.gameObject.SetActive(false);
    }

    public void SetWeatherToWindy()
    {

    }

    public void SetWeather(string weather)
    {
        if (weather.Equals("rainy"))
        {
            SetWeatherToRainy();
        }
        else if (weather.Equals("sunny"))
        {
            SetWeatherToSunny();
        }
        else if (weather.Equals("windy"))
        {
            SetWeatherToWindy();
        }
        else if (weather.Equals("snowy"))
        {
            SetWeatherToSnow();
        }
    }
    public void AddFert()
    {
        connector.RequestFertilizer(40, 0.7f);
    }

    public void ShowMessageText(string message)
    {
        MessageText.text = message;
    }

    public void ResetMessageText()
    {
        MessageText.text = "";
    }
}
