using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;
using TMPro;

public class ColorCard : CardTypeBase
{
    [SerializeField] public Color colorSelected;
    [SerializeField] public TextMeshProUGUI colorText;
    [SerializeField] public Sprite spriteUniform;
    [SerializeField] public Sprite spriteEdge;
    Color[] colorList = new Color[6] { Color.red , Color.green, Color.blue,
        Color.cyan, Color.magenta, Color.yellow} ;
    string[] textList = new string[6] { "green", "blue", "red", "magenta", "yellow", "cyan"};

    Color[] colorListGray = new Color[9] { new Color(0.1f, 0.1f, 0.1f),
        new Color(0.2f, 0.2f, 0.2f), new Color(0.3f, 0.3f, 0.3f),
        new Color(0.4f, 0.4f, 0.4f), new Color(0.5f, 0.5f, 0.5f),
        new Color(0.6f, 0.6f, 0.6f), new Color(0.7f, 0.7f, 0.7f),
        new Color(0.8f, 0.8f, 0.8f), new Color(0.9f, 0.9f, 0.9f) };

    SpriteRenderer colorRenderer;
    SpriteRenderer colorRendererEdge;
    Color colorInitial;
    string modeColor = "add";
    Color colorEmpty = Color.clear;
    Color colorEssential1;
    Color colorEssential2;
    Color colorEssential3;
    Color colorMix1;
    Color colorMix2;
    Color colorMix3;
    Color colorNull;
    public int colorIndexGray;
    string textEmpty;
    string textSelected;

    protected override void Start()
    {
        base.Start();
        if (cardFrameAttached != null && cardFrameAttached.IsInitialized)
            return; // ActivateComponents() already set our values
        SetColorsForMode();
        colorInitial = SetColor();
    }

    public void SetColorsForMode()
    {
        if (modeColor == "add" || modeColor == "text")
        {
            colorEssential1 = Color.red;
            colorEssential2 = Color.green;
            colorEssential3 = Color.blue;
            colorMix1 = Color.yellow;
            colorMix2 = Color.cyan;
            colorMix3 = Color.magenta;
            colorNull = Color.white;
        }
        else if (modeColor == "subtract")
        {
            colorEssential1 = Color.cyan;
            colorEssential2 = Color.magenta;
            colorEssential3 = Color.yellow;
            colorMix1 = Color.blue;
            colorMix2 = Color.red;
            colorMix3 = Color.green;
            colorNull = Color.black;
        }
        else if (modeColor == "gray")
        {
            colorNull = new Color(1f, 1f, 1f);
        }
    }

    public Color SetColor()
    {
        colorSelected = colorEmpty;
        textEmpty = "none";

        SpriteRenderer[] renderersColor;
        renderersColor = GetComponentsInChildren<SpriteRenderer>();

        foreach(SpriteRenderer rendererIter in renderersColor)
        {
            if(rendererIter.gameObject.name == "Color Area")
            {
                colorRenderer = rendererIter;
                if(modeColor == "text")
                {
                    colorRenderer.gameObject.SetActive(false);
                }
            }
            else
            {
                colorRendererEdge = rendererIter;
                if(modeColor == "add" || modeColor == "subtract" || modeColor == "gray" || modeColor == "text")
                {
                    colorRendererEdge.gameObject.SetActive(false);
                }
            }
        }

        cardAttached = cardFrameAttached.cardObject;
        
        //colorTextObject = GetComponentInParent<ColorText>();
        //colorTextObject.gameObject.SetActive(true);
        //colorText = GetComponentInChildren<Text>();
        if (modeColor != "text")
        {
            //colorTextObject.gameObject.SetActive(false);
            colorText.gameObject.SetActive(false);

        }

        if (activated)
        {
            if (modeColor == "add" || modeColor == "subtract")
            {
                int randomIndex = Random.Range(0, colorList.Length);
                colorSelected = colorList[randomIndex];
            }
            else if (modeColor == "gray")
            {
                int randomIndex = Random.Range(0, colorListGray.Length);
                colorIndexGray = randomIndex + 1;
                colorSelected = colorListGray[randomIndex];
            }
            else if (modeColor == "text")
            {
                int randomIndex = Random.Range(0, colorList.Length);
                colorSelected = colorList[randomIndex];
                textSelected = textList[randomIndex];
            }

        }
        if (cardSuper)
        {
            colorSelected = colorNull;
        }
        
        if(modeColor == "text")
        {
            colorText.gameObject.SetActive(true);
            colorText.text = textSelected;
            colorText.color = colorSelected;

        }
        else
        {
            colorRenderer.color = colorSelected;
        }
 
        return colorSelected;
    }

    public void SetActivated(bool activatedValue)
    {
        activated = activatedValue;
    }

    public float ComputeMergeColorGain(Color newColor, int colorIndexGrayNew)
    {
        Color oldColor = colorSelected;

        if (modeColor == "add" || modeColor == "subtract" || modeColor == "text")
        {
            
            if (newColor == colorEmpty)
            {
                return 0f;
            }

            if (oldColor == colorEmpty)
            {
                return 0f;
            }

            if (oldColor != colorNull && oldColor == newColor)
            {
                return -1f;
            }

            if (oldColor == colorNull && newColor != colorNull)
            {
                return -1f;
            }

            if (oldColor == colorNull && newColor == colorNull)
            {
                return 3f;
            }

            if (oldColor != colorNull && newColor == colorNull)
            {
                return 0f;
            }

            if ((oldColor == colorEssential1 && newColor == colorEssential2) ||
                (oldColor == colorEssential2 && newColor == colorEssential1))
            {
                return 1f;
            }
            if ((oldColor == colorEssential1 && newColor == colorEssential3) ||
                (oldColor == colorEssential3 && newColor == colorEssential1))
            {
                return 1f;
            }
            if ((oldColor == colorEssential3 && newColor == colorEssential2) ||
                (oldColor == colorEssential2 && newColor == colorEssential3))
            {
                return 1f;
            }
            if ((oldColor == colorMix3 && newColor == colorMix1) ||
                (oldColor == colorMix1 && newColor == colorMix3))
            {
                return 2f;
            }
            if ((oldColor == colorMix3 && newColor == colorMix2) ||
                (oldColor == colorMix2 && newColor == colorMix3))
            {
                return 2f;
            }
            if ((oldColor == colorMix2 && newColor == colorMix1) ||
                (oldColor == colorMix1 && newColor == colorMix2))
            {
                return 2f;
            }
            if ((oldColor == colorMix2 && newColor == colorEssential1) ||
                (oldColor == colorEssential1 && newColor == colorMix2))
            {
                return 2f;
            }
            if ((oldColor == colorMix3 && newColor == colorEssential2) ||
                (oldColor == colorEssential2 && newColor == colorMix3))
            {
                return 2f;
            }
            if ((oldColor == colorEssential3 && newColor == colorMix1) ||
                (oldColor == colorMix1 && newColor == colorEssential3))
            {
                return 2f;
            }
            if ((oldColor == colorEssential1 && newColor == colorMix3) ||
                (oldColor == colorMix3 && newColor == colorEssential1))
            {
                return -1f;
            }
            if ((oldColor == colorEssential1 && newColor == colorMix1) ||
                (oldColor == colorMix1 && newColor == colorEssential1))
            {
                return -1f;
            }
            if ((oldColor == colorEssential2 && newColor == colorMix1) ||
                (oldColor == colorMix1 && newColor == colorEssential2))
            {
                return -1f;
            }
            if ((oldColor == colorEssential2 && newColor == colorMix2) ||
                (oldColor == colorMix2 && newColor == colorEssential2))
            {
                return -1f;
            }
            if ((oldColor == colorEssential3 && newColor == colorMix3) ||
               (oldColor == colorMix3 && newColor == colorEssential3))
            {
                return -1f;
            }
            if ((oldColor == colorEssential3 && newColor == colorMix2) ||
                (oldColor == colorMix2 && newColor == colorEssential3))
            {
                return -1f;
            }
        }

        else if (modeColor == "gray")
        {
            if (newColor == colorEmpty)
            {
                return 0f;
            }

            if (oldColor == colorEmpty)
            {
                return 0f;
            }

            if (oldColor != colorNull && oldColor == newColor)
            {
                return -1f;
            }

            if (oldColor == colorNull && newColor != colorNull)
            {
                return -1f;
            }

            if (oldColor == colorNull && newColor == colorNull)
            {
                return 3f;
            }

            if (oldColor != colorNull && newColor == colorNull)
            {
                return 0f;
            }

            //Logic starts here
            int newIndex = colorIndexGray + colorIndexGrayNew;
            if (colorIndexGray > colorIndexGrayNew)
            {
                if (newIndex > 9)
                {
                    return 2f;
                }
                else
                {
                    return 1f;
                }
            }
            else
            {
                return -1f;
            }
        }

        return 0f;
    }

    public void MergeColorCard(Color newColor, int colorIndexGrayNew)
    {
        Color oldColor = colorSelected;

        if (modeColor == "add" || modeColor == "subtract")
        {
            if (newColor == colorEmpty)
            {
                return;
            }

            if (oldColor == colorEmpty)
            {
                colorRenderer.color = newColor;
                colorSelected = colorRenderer.color;
                return;
            }

            if (oldColor != colorNull && oldColor == newColor)
            {
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                return;
            }

            if (oldColor == colorNull && newColor != colorNull)
            {
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                return;
            }

            if (oldColor == colorNull && newColor == colorNull)
            {
                cardAttached.ChangeCardMana(manaIncreaseMultiplier3);
                return;
            }

            if (oldColor != colorNull && newColor == colorNull)
            {
                colorRenderer.color = colorNull;
                colorSelected = colorRenderer.color;
                return;
            }

            if ((oldColor == colorEssential1 && newColor == colorEssential2) ||
                (oldColor == colorEssential2 && newColor == colorEssential1))
            {
                colorRenderer.color = colorMix1;
                colorSelected = colorRenderer.color;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                return;
            }
            if ((oldColor == colorEssential1 && newColor == colorEssential3) ||
                (oldColor == colorEssential3 && newColor == colorEssential1))
            {
                colorRenderer.color = colorMix3;
                colorSelected = colorRenderer.color;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                return;
            }
            if ((oldColor == colorEssential3 && newColor == colorEssential2) ||
                (oldColor == colorEssential2 && newColor == colorEssential3))
            {
                colorRenderer.color = colorMix2;
                colorSelected = colorRenderer.color;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                return;
            }
            if ((oldColor == colorMix3 && newColor == colorMix1) ||
                (oldColor == colorMix1 && newColor == colorMix3))
            {
                colorRenderer.color = colorNull;
                colorSelected = colorRenderer.color;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier2);
                return;
            }
            if ((oldColor == colorMix3 && newColor == colorMix2) ||
                (oldColor == colorMix2 && newColor == colorMix3))
            {
                colorRenderer.color = colorNull;
                colorSelected = colorRenderer.color;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier2);
                return;
            }
            if ((oldColor == colorMix2 && newColor == colorMix1) ||
                (oldColor == colorMix1 && newColor == colorMix2))
            {
                colorRenderer.color = colorNull;
                colorSelected = colorRenderer.color;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier2);
                return;
            }
            if ((oldColor == colorMix2 && newColor == colorEssential1) ||
                (oldColor == colorEssential1 && newColor == colorMix2))
            {
                colorRenderer.color = colorNull;
                colorSelected = colorRenderer.color;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier2);
                return;
            }
            if ((oldColor == colorMix3 && newColor == colorEssential2) ||
                (oldColor == colorEssential2 && newColor == colorMix3))
            {
                colorRenderer.color = colorNull;
                colorSelected = colorRenderer.color;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier2);
                return;
            }
            if ((oldColor == colorEssential3 && newColor == colorMix1) ||
                (oldColor == colorMix1 && newColor == colorEssential3))
            {
                colorRenderer.color = colorNull;
                colorSelected = colorRenderer.color;
                cardAttached.ChangeCardMana(manaIncreaseMultiplier2);
                return;
            }
            if ((oldColor == colorEssential1 && newColor == colorMix3) ||
                (oldColor == colorMix3 && newColor == colorEssential1))
            {
                colorRenderer.color = colorMix3;
                colorSelected = colorRenderer.color;
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                return;
            }
            if ((oldColor == colorEssential1 && newColor == colorMix1) ||
                (oldColor == colorMix1 && newColor == colorEssential1))
            {
                colorRenderer.color = colorMix1;
                colorSelected = colorRenderer.color;
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                return;
            }
            if ((oldColor == colorEssential2 && newColor == colorMix1) ||
                (oldColor == colorMix1 && newColor == colorEssential2))
            {
                colorRenderer.color = colorMix1;
                colorSelected = colorRenderer.color;
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                return;
            }
            if ((oldColor == colorEssential2 && newColor == colorMix2) ||
                (oldColor == colorMix2 && newColor == colorEssential2))
            {
                colorRenderer.color = colorMix2;
                colorSelected = colorRenderer.color;
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                return;
            }
            if ((oldColor == colorEssential3 && newColor == colorMix3) ||
               (oldColor == colorMix3 && newColor == colorEssential3))
            {
                colorRenderer.color = colorMix3;
                colorSelected = colorRenderer.color;
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                return;
            }
            if ((oldColor == colorEssential3 && newColor == colorMix2) ||
                (oldColor == colorMix2 && newColor == colorEssential3))
            {
                colorRenderer.color = colorMix2;
                colorSelected = colorRenderer.color;
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                return;
            }
        }

        else if (modeColor == "gray")
        {
            if (newColor == colorEmpty)
            {
                return;
            }

            if (oldColor == colorEmpty)
            {
                colorRenderer.color = newColor;
                colorSelected = colorRenderer.color;
                return;
            }

            if (oldColor != colorNull && oldColor == newColor)
            {
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                return;
            }

            if (oldColor == colorNull && newColor != colorNull)
            {
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                return;
            }

            if (oldColor == colorNull && newColor == colorNull)
            {
                cardAttached.ChangeCardMana(manaIncreaseMultiplier3);
                return;
            }

            if (oldColor != colorNull && newColor == colorNull)
            {
                colorRenderer.color = colorNull;
                colorSelected = colorRenderer.color;
                return;
            }

            //Logic starts here
            int newIndex = colorIndexGray + colorIndexGrayNew;
            if (colorIndexGray > colorIndexGrayNew)
            {
                if (newIndex > 9)
                {
                    colorIndexGray = 10;
                    colorRenderer.color = colorNull;
                    colorSelected = colorRenderer.color;
                    cardAttached.ChangeCardMana(manaIncreaseMultiplier2);
                    return;
                }
                else
                {
                    colorIndexGray = newIndex;
                    colorSelected = colorListGray[colorIndexGray-1];
                    cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                    colorRenderer.color = colorSelected;
                    return;
                }
            }
            else
            {
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                return;
            }
            

        }

        else if(modeColor == "text")
        {
            if (newColor == colorEmpty)
            {
                return;
            }

            if (oldColor == colorEmpty)
            {
                colorSelected = newColor;
                setColorText();
                return;
            }

            if (oldColor != colorNull && oldColor == newColor)
            {
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                return;
            }

            if (oldColor == colorNull && newColor != colorNull)
            {
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                return;
            }

            if (oldColor == colorNull && newColor == colorNull)
            {
                cardAttached.ChangeCardMana(manaIncreaseMultiplier3);
                return;
            }

            if (oldColor != colorNull && newColor == colorNull)
            {
                colorSelected = colorNull;
                setColorText();
                return;
            }

            if ((oldColor == colorEssential1 && newColor == colorEssential2) ||
                (oldColor == colorEssential2 && newColor == colorEssential1))
            {
                colorSelected = colorMix1;
                setColorText();
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                return;
            }
            if ((oldColor == colorEssential1 && newColor == colorEssential3) ||
                (oldColor == colorEssential3 && newColor == colorEssential1))
            {
                colorSelected = colorMix3;
                setColorText();
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                return;
            }
            if ((oldColor == colorEssential3 && newColor == colorEssential2) ||
                (oldColor == colorEssential2 && newColor == colorEssential3))
            {
                colorSelected = colorMix2;
                setColorText();
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                return;
            }
            if ((oldColor == colorMix3 && newColor == colorMix1) ||
                (oldColor == colorMix1 && newColor == colorMix3))
            {
                colorSelected = colorNull;
                setColorText();
                cardAttached.ChangeCardMana(manaIncreaseMultiplier2);
                return;
            }
            if ((oldColor == colorMix3 && newColor == colorMix2) ||
                (oldColor == colorMix2 && newColor == colorMix3))
            {
                colorSelected = colorNull;
                setColorText();
                cardAttached.ChangeCardMana(manaIncreaseMultiplier2);
                return;
            }
            if ((oldColor == colorMix2 && newColor == colorMix1) ||
                (oldColor == colorMix1 && newColor == colorMix2))
            {
                colorSelected = colorNull;
                setColorText();
                cardAttached.ChangeCardMana(manaIncreaseMultiplier2);
                return;
            }
            if ((oldColor == colorMix2 && newColor == colorEssential1) ||
                (oldColor == colorEssential1 && newColor == colorMix2))
            {
                colorSelected = colorNull;
                setColorText();
                cardAttached.ChangeCardMana(manaIncreaseMultiplier2);
                return;
            }
            if ((oldColor == colorMix3 && newColor == colorEssential2) ||
                (oldColor == colorEssential2 && newColor == colorMix3))
            {
                colorSelected = colorNull;
                setColorText();
                cardAttached.ChangeCardMana(manaIncreaseMultiplier2);
                return;
            }
            if ((oldColor == colorEssential3 && newColor == colorMix1) ||
                (oldColor == colorMix1 && newColor == colorEssential3))
            {
                colorSelected = colorNull;
                setColorText();
                cardAttached.ChangeCardMana(manaIncreaseMultiplier2);
                return;
            }
            if ((oldColor == colorEssential1 && newColor == colorMix3) ||
                (oldColor == colorMix3 && newColor == colorEssential1))
            {
                colorSelected = colorMix3;
                setColorText();
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                return;
            }
            if ((oldColor == colorEssential1 && newColor == colorMix1) ||
                (oldColor == colorMix1 && newColor == colorEssential1))
            {
                colorSelected = colorMix1;
                setColorText();
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                return;
            }
            if ((oldColor == colorEssential2 && newColor == colorMix1) ||
                (oldColor == colorMix1 && newColor == colorEssential2))
            {
                colorSelected = colorMix1;
                setColorText();
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                return;
            }
            if ((oldColor == colorEssential2 && newColor == colorMix2) ||
                (oldColor == colorMix2 && newColor == colorEssential2))
            {
                colorSelected = colorMix2;
                setColorText();
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                return;
            }
            if ((oldColor == colorEssential3 && newColor == colorMix3) ||
               (oldColor == colorMix3 && newColor == colorEssential3))
            {
                colorSelected = colorMix3;
                setColorText();
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                return;
            }
            if ((oldColor == colorEssential3 && newColor == colorMix2) ||
                (oldColor == colorMix2 && newColor == colorEssential3))
            {
                colorSelected = colorMix2;
                setColorText();
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                return;
            }
        }
        
    }

    public void setColorCard(Color colorCard)
    {
        colorRenderer.color = colorCard;
    }

    public void setColorText()
    {
        if(colorSelected == Color.white)
        {
            colorText.text = "white";
            colorText.color = Color.white;
        }
        else
        {
            colorText.text = textList[System.Array.FindIndex(colorList, x => x == colorSelected)];
            textSelected = colorText.text;
            colorText.color = colorSelected;
        }
        
    }

    public void SetModeColor(string modeColorSet)
    {
        modeColor = modeColorSet;
        SetColorsForMode();
    }

    public string GetModeColor()
    {
        return modeColor;
    }


}
