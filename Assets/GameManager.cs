using NUnit.Framework;
using System.Collections.Generic;
using UnityEngine;

public class GameManager : MonoBehaviour
{
    float TotalTime;
    float phaseTime;
    [SerializeField] float Phase1Duration;
    [SerializeField] float Phase2Duration;
    [SerializeField] float Phase3Duration;

    public enum Phase { one, two, three }
    [SerializeField] Phase phase = Phase.one;
    public List<GameObject> Farms;

    private void Awake()
    {
        Seed seed = GetComponent<Seed>();
        foreach(var farm in Farms)
        {
            farm.GetComponent<Farm>().SetPlotSprites(seed.phase1sprite, seed.phase2sprite, seed.phase3sprite);
        }
    }

    private void FixedUpdate()
    {
        if(phase == Phase.one && phaseTime>Phase1Duration)
        {
            ChangeAllFarmsToPhase2();
        }
        if(phase == Phase.two && phaseTime > Phase2Duration)
        {
            ChangeAllFarmsToPhase3();
        }


        TotalTime += Time.fixedDeltaTime;
        phaseTime += Time.fixedDeltaTime;
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


}
