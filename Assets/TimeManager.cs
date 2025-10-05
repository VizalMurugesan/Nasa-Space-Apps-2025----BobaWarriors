using UnityEngine;
using UnityEngine.UI;
using TMPro;
using System;
using NUnit.Framework;
using System.Collections.Generic;

public class TimeManager : MonoBehaviour
{
    public enum Timeoftheday { Morning,Evening,Night}
    Timeoftheday time = Timeoftheday.Morning;

    public enum ManagerState { Basking, Transitioning}
    ManagerState State = ManagerState.Basking;

    public enum Weather { Rainy, Sunny, Humid, Windy, snowy}
    Weather weather = Weather.Sunny;
    public Image WeatherPanel;

    [SerializeField]float MorningDuration;
    [SerializeField]float EveningDuration;
    [SerializeField]float NightDuration;
    [SerializeField] float Transitionduration;
    [SerializeField] TextMeshProUGUI DayCountText;

    public int DayCount;

    
    public TimeOfTheDay currentTimeOfTheDay;

    public Image image;
   
    Color imageColor;

    public SpriteRenderer SnowSprite;

    //TimeOfTheDay nextTime;
    public float TotalTime = 0f;
    float currentTimeCurrentduration = 0f;
    float TransitionTimeCurrentduration = 0f;

    public float GameSpeed = 1f;



    private void Awake()
    {
        TimeOfTheDay Morning = new TimeOfTheDay(MorningDuration, new Vector4(0f, 0f, 0f, 0f), Timeoftheday.Morning);
        TimeOfTheDay Evening = new TimeOfTheDay(EveningDuration, new Vector4(100f/255f, 0f, 50f/255f, 150f / 255f), Timeoftheday.Evening);
        TimeOfTheDay Night = new TimeOfTheDay(NightDuration, new Vector4(0f, 0f, 50f / 255f, 200f/255f), Timeoftheday.Night);
        Morning.SetNextTime(Evening);
        Evening.SetNextTime(Night);
        Night.SetNextTime(Morning);
        imageColor = image.color;
        currentTimeOfTheDay = Morning;
        
        

    }
    public void Update()
    {
        if (State.Equals(ManagerState.Basking))
        {
            
            currentTimeCurrentduration += Time.deltaTime;
            if (currentTimeCurrentduration >= currentTimeOfTheDay.GetTimeDuration())
            {
                ChangeStateToTransitioning();
            }
        }
        else if (State.Equals(ManagerState.Transitioning))
        {
            
            Vector4 ColorVector = Vector4.Lerp(currentTimeOfTheDay.GetRGBval(),
            currentTimeOfTheDay.GetNextTimeOfTheDay().GetRGBval(), TransitionTimeCurrentduration / Transitionduration);

            imageColor.r = ColorVector.x; imageColor.g = ColorVector.y;
            imageColor.b = ColorVector.z; imageColor.a = ColorVector.w;
            image.color = imageColor;

            TransitionTimeCurrentduration += Time.deltaTime;

            if(TransitionTimeCurrentduration >= Transitionduration / 2)
            {
                ChangeSpriteAndTextToCurrent();
            }

            if(TransitionTimeCurrentduration>= Transitionduration)
            {
                ChangeStateToBasking();
            }
        }
        

        TotalTime += Time.deltaTime;
        
    }

   

    void ChangeToNextTime()
    {
        currentTimeOfTheDay = currentTimeOfTheDay.GetNextTimeOfTheDay();
        //currentTimeCurrentduration = 0f;
       
    }

    void ChangeStateToBasking()
    {
        State = ManagerState.Basking;
        ChangeToNextTime();
        CalculateWeather();
       
        TransitionTimeCurrentduration = 0f;
        currentTimeCurrentduration = 0f;
    }

    void ChangeSpriteAndTextToCurrent()
    {
        time = currentTimeOfTheDay.GetNextTimeOfTheDay().GetTime();
        
    }

    void ChangeStateToTransitioning()
    {
        
        State = ManagerState.Transitioning;
        TransitionTimeCurrentduration = 0f;
        currentTimeCurrentduration = 0f;
    }

    public void CalculateWeather()
    {
        if (time.Equals(Timeoftheday.Morning))
        {
            //Debug.Log("weather changed");
            
            DayCount++;
            DayCountText.text = "Days : " + DayCount;
        }
            
    }

    public void IncreaseGameSpeed()
    {
        GameSpeed = Mathf.Clamp(GameSpeed *= 2, 1f, 20f);
        Time.timeScale = GameSpeed;
    }
    public void DecreaseGameSpeed()
    {
        GameSpeed = Mathf.Clamp(GameSpeed /= 2, 1f, 20f);
        Time.timeScale = GameSpeed;
    }


}

public class TimeOfTheDay
{
    float duration;
    Vector4 RGBval;
    TimeManager.Timeoftheday time;
    TimeOfTheDay nextTime;
    
    

    

    public TimeOfTheDay(float duration, Vector4 RGBval, TimeManager.Timeoftheday time)
    {
        this.duration = duration;
        this.RGBval = RGBval;
        this.time = time;
        
    }

    public void SetNextTime(TimeOfTheDay nextTime)
    {
        this.nextTime = nextTime;
    }
    
    public TimeOfTheDay GetNextTimeOfTheDay()
    {
        return this.nextTime;
    }

    public TimeManager.Timeoftheday GetTime()
    {
        return this.time;
    }

    public float GetTimeDuration()
    {
        return this.duration;
    }

    public Vector4 GetRGBval()
    {
        return RGBval;
    }

    
}

