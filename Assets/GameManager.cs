using NUnit.Framework;
using System.Collections.Generic;
using TMPro;
using UnityEngine;

public class GameManager : MonoBehaviour
{
    public static GameManager Instance { get; private set; }
    float TotalTime;
    float phaseTime;
    [SerializeField] float Phase1Duration;
    [SerializeField] float Phase2Duration;
    [SerializeField] float Phase3Duration;
    public TimeManager timeManager;

    public enum Area { polar, Temperate, tropical, Equitorial}

    public enum Phase { one, two, three, Four }
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
    }

    private void Update()
    {
        if (HasChosenDate && HasChosenMap&& HasPloughed && HasSownSeed)
        {
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
    }

    void ChangeAllFarmsToPhase3()
    {
        foreach (var farm in Farms)
        {
            farm.GetComponent<Farm>().ChangeAllPlotToPhase3();

        }
        phase = Phase.three;
        phaseTime = 0f;
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
        TemperatureText.text = "Temp: " + value;

    }

    public void SetIrrigationTypeToNone()
    {
        irrigationtype = IrrigationType.None;
        irrigationPanel.SetActive(false);

    }

    public void SetIrrigationTypeToDrip()
    {
        irrigationtype = IrrigationType.drip;
        irrigationPanel.SetActive(false);

    }
    public void SetIrrigationTypeToHigh()
    {
        irrigationtype = IrrigationType.high;
        irrigationPanel.SetActive(false);

    }

    public void OpenIrrigationPanel()
    {
        irrigationPanel.SetActive(true);
    }

    public void Plough()
    {
        HasPloughed = true;

    }

    public void SowSeed()
    {
        HasSownSeed = true;
        Time.timeScale = 1f;
    }

    public void ClickOnWorldmap()
    {
        worldmap.SetActive(false);
        HasChosenMap = true;

    }
}
