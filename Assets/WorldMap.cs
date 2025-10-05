using UnityEngine;
using UnityEngine.EventSystems;

public class WorldMap : MonoBehaviour, IPointerClickHandler
{
    void IPointerClickHandler.OnPointerClick(PointerEventData eventData)
    {
        if(eventData.button == PointerEventData.InputButton.Left)
        {
            GameManager.Instance.HasChosenMap = true;
            GameManager.Instance.CheckForArea((Vector2)eventData.position);
            
        }
        
    }
}
