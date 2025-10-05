using System.Collections;
using TMPro;
using Unity.VisualScripting;
using UnityEngine;
using UnityEngine.UI;

public class UIBar : MonoBehaviour
{
    public float MaximumValue;
    public float CurrentValue;
   

    public Image BarImage;

    public TMP_Text value;

    public string Unit;
    
    public enum Valtype { FLOAT,INT}
    public Valtype Val;

    public void AddValue(float Value)
    {
        CurrentValue = Mathf.Clamp(CurrentValue + Value, 0f, MaximumValue);
        UpdateUI();
    }

    public void ChangeValue(float Value)
    {
        CurrentValue = Mathf.Clamp(Value, 0f, MaximumValue);
        UpdateUI();
    }

    void UpdateUI()
    {
        float value = CurrentValue / MaximumValue;
        BarImage.fillAmount = value;

        if(Val.Equals(Valtype.INT))
        {
            this.value.text = (int)CurrentValue + " " + Unit;
        }
        if(Val.Equals(Valtype.FLOAT))
        {
            this.value.text = CurrentValue + " " + Unit;
        }
        
    }

    

    public bool IsBarFull()
    {
        if(CurrentValue == MaximumValue)
        {
            return true;
        }
        return false;
    }
}
