using NUnit.Framework;
using System.Collections.Generic;
using UnityEngine;

public class DateMonthChoiceManager : MonoBehaviour
{
    public List<GameObject> Months;
    public List<GameObject> Days;

    Dictionary< int, GameObject> MonthAndValue;
    Dictionary<int, GameObject> DaysAndValue;

    public void SetMonths()
    {
        for (int i = 1; i<= Months.Count; i++)
        {
            MonthAndValue.Add(i, Months[i-1]);
        }
    }
    public void SetDays()
    {
        for (int i = 1; i <= Days.Count; i++)
        {
            DaysAndValue.Add(i, Days[i - 1]);
        }
    }

    public void Start()
    {
        SetDays();
        SetMonths();
    }

    public void OnClickingButtonMonth(GameObject button)
    {
        Debug.Log("you clicked" + button.name);
    }
}
