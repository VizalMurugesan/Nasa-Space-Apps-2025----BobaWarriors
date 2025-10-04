using NUnit.Framework;
using System.Collections.Generic;
using UnityEngine;

public class Farm : MonoBehaviour
{
    public List<GameObject> farmPlots;

    public void ChangeAllPlotToPhase1()
    {
        foreach (var plot in farmPlots)
        {
            plot.GetComponent<FarmPlot>().ChangeStateToPhase1 ();
        }
    }
    public void ChangeAllPlotToPhase2()
    {
        foreach (var plot in farmPlots)
        {
            plot.GetComponent<FarmPlot>().ChangeStateToPhase2();
        }
    }
    public void ChangeAllPlotToPhase3()
    {
        foreach (var plot in farmPlots)
        {
            plot.GetComponent<FarmPlot>().ChangeStateToPhase3();
        }
    }

    public void SetPlotSprites(Sprite one, Sprite two, Sprite three)
    {
        foreach(var plot in farmPlots)
        {
            plot.GetComponent<FarmPlot>().SetSprites(one, two, three);
        }
    }
}
