using NUnit.Framework;
using System.Collections.Generic;
using UnityEngine;

public class GameManager : MonoBehaviour
{
    public static GameManager Instance { get; private set; }
    float TotalTime;
    float phaseTime;
    [SerializeField] float Phase1Duration;
    [SerializeField] float Phase2Duration;
    [SerializeField] float Phase3Duration;

    public enum Area { polar, Temperate, tropical, Equitorial}

    public enum Phase { one, two, three }
    [SerializeField] Phase phase = Phase.one;
    public List<GameObject> Farms;

    

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
    }

    private void Update()
    {
        if(phase == Phase.one && phaseTime>Phase1Duration)
        {
            ChangeAllFarmsToPhase2();
        }
        if(phase == Phase.two && phaseTime > Phase2Duration)
        {
            ChangeAllFarmsToPhase3();
        }


        TotalTime += Time.deltaTime;
        phaseTime += Time.deltaTime;
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
        Debug.Log("polar");
    }

    public void SetAreaTemperate()
    {
        Debug.Log("Temperate");
    }
    public void SetAreaTropical()
    {
        Debug.Log("Tropical");
    }

    public void SetAreaEquitorial()
    {
        Debug.Log("Equitorial");

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
}
