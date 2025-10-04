using UnityEngine;
using UnityEngine.EventSystems;

public class WorldMap : MonoBehaviour, IPointerClickHandler
{
    void IPointerClickHandler.OnPointerClick(PointerEventData eventData)
    {
        if(eventData.button == PointerEventData.InputButton.Left)
        {
            Debug.Log("Clicked at: " + eventData.position);
            GameManager.Instance.CheckForArea((Vector2)eventData.position);
            Debug.Log("clicked");
        }
        if (eventData.button == PointerEventData.InputButton.Right)
        {
            Debug.Log("Clicked at: " + eventData.position);
            GameManager.Instance.CheckForArea((Vector2)eventData.position);
            Debug.Log("clicked");
        }
    }
}
