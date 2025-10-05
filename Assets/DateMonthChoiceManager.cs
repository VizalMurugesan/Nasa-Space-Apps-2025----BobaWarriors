using NUnit.Framework;
using System.Collections.Generic;
using UnityEngine;

public class DateMonthChoiceManager : MonoBehaviour
{
    public List<GameObject> Months;
    public List<GameObject> days;

    
    Dictionary<int,GameObject> DaysAndValue;
    Dictionary<int, GameObject> MonthAndValue;

    int DaySelected;
    int MonthSelected;

    bool isDaySelected;
    bool isMonthSelected;
    

    public void Awake()
    {
        MonthAndValue = new Dictionary<int, GameObject>();
        DaysAndValue = new Dictionary<int, GameObject>();
        SetDays();
        SetMonths();
    }
    public void SetMonths()
    {
        for (int i = 1; i<= Months.Count; i++)
        {
            MonthAndValue.Add(i,Months[i-1].gameObject);
        }
    }
    public void SetDays()
    {
        for (int i = 1; i <= days.Count; i++)
        {
            
            DaysAndValue.Add(i, days[i-1].gameObject);
        }
    }

    

    public void OnClickingDayButton(GameObject button)
    {
        Debug.Log("You clicked " + button.name);

        int dayVal = -1;
        foreach (var pair in DaysAndValue)
        {
            if (pair.Value == button)
            {
                dayVal = pair.Key;
                break;
            }
        }

        if (dayVal == -1)
        {
            Debug.LogWarning("Day button not found in dictionary!");
            return;
        }

        Debug.Log($"You clicked day {dayVal}");

        // Hide invalid month buttons (e.g. if day = 31, only show months with 31 days)
        UpdateMonthsUI(dayVal);
        DaySelected = dayVal;
        isDaySelected = true;
        if (isMonthSelected && isDaySelected)
        {
            GameManager.Instance.SowDay = DaySelected;
            GameManager.Instance.SowMonth = MonthSelected;
            gameObject.SetActive(false);
        }
    }
    public void OnClickingMonthButton(GameObject button)
    {
        int monthVal = -1;
        foreach (var pair in MonthAndValue)
        {
            if (pair.Value == button)
            {
                monthVal = pair.Key;
                break;
            }
        }

        if (monthVal == -1)
        {
            Debug.LogWarning("Month button not found in dictionary!");
            return;
        }

        int maxDayCount = GetMaxDayCount(monthVal);
        Debug.Log($"You clicked month {monthVal}, which has {maxDayCount} days.");

        // OPTIONAL: deactivate days beyond maxDayCount
        UpdateDaysUI(maxDayCount);
        MonthSelected = monthVal;
        isMonthSelected = true;

        if(isMonthSelected && isDaySelected)
        {
            GameManager.Instance.SowDay = DaySelected;
            GameManager.Instance.SowMonth = MonthSelected;
            gameObject.SetActive(false);
        }
    }
    public int GetMaxDayCount(int month)
    {
        switch (month)
        {
            case 1:  // January
            case 3:  // March
            case 5:  // May
            case 7:  // July
            case 8:  // August
            case 10: // October
            case 12: // December
                return 31;

            case 4:  // April
            case 6:  // June
            case 9:  // September
            case 11: // November
                return 30;

            case 2:  // February
                return 28; // or 29 in leap year

            default:
                Debug.LogWarning("Invalid month number: " + month);
                return 0;
        }

    }
    public int GetMaxMonthCount(int day)
    {
        // Counts how many months can have this day
        int count = 0;
        for (int month = 1; month <= 12; month++)
        {
            if (day <= GetMaxDayCount(month))
            {
                count++;
            }
        }
        return count;
    }

    public void UpdateMonthsUI(int selectedDay)
    {
        for (int i = 1; i <= MonthAndValue.Count; i++)
        {
            GameObject monthObj = MonthAndValue[i];
            int maxDay = GetMaxDayCount(i);

            // only show months that have at least this day
            monthObj.SetActive(selectedDay <= maxDay);
        }

        int validMonthCount = GetMaxMonthCount(selectedDay);
        Debug.Log($"Day {selectedDay} exists in {validMonthCount} months.");
    }

    public void UpdateDaysUI(int maxDays)
    {
        for (int i = 1; i <= DaysAndValue.Count; i++)
        {
            GameObject dayObj = DaysAndValue[i];
            dayObj.SetActive(i <= maxDays);
        }
    }


}



