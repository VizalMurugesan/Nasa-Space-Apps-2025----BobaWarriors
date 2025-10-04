using UnityEngine;

public class FarmPlot : MonoBehaviour
{
    Sprite spritePhase1;
    Sprite spritePhase2;
    Sprite spritePhase3;
    Vector2 scale;
    public SpriteRenderer spriteRenderer;
    public RectTransform rectTransform;



    public enum PlantType { }
    PlantType type;

    public void Awake()
    {
        spriteRenderer = GetComponent<SpriteRenderer>();
        rectTransform = GetComponent<RectTransform>();
    }

    public void ChangeStateToPhase1()
    {
        
        spriteRenderer.sprite = spritePhase1;
        rectTransform.localScale = new Vector2(0.25f, 0.25f);
        
    }
    public void ChangeStateToPhase2()
    {
        
        spriteRenderer.sprite = spritePhase2;
        rectTransform.localScale = new Vector2(0.5f, 0.5f);

    }

    public void ChangeStateToPhase3()
    {
        
        spriteRenderer.sprite = spritePhase3;
        rectTransform.localScale = new Vector2(0.75f, 0.75f);
    }

    public void SetSprites( Sprite one, Sprite two, Sprite three)
    {
        spritePhase1 = one;
        spritePhase2 = two;
        spritePhase3 = three;

        ChangeStateToPhase1();
    }

}
