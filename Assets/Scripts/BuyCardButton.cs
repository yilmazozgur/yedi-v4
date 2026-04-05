using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;
using BayatGames.SaveGameFree;

public class BuyCardButton : MonoBehaviour
{
    [SerializeField] public float cardType;
    [SerializeField] float costMultiplier = 10f;
    [SerializeField] float cardCost;
    [SerializeField] float cardCostSuper;
    [SerializeField] public bool disabled = false;
    [SerializeField] public bool enableByDefault = false;
    [SerializeField] public bool enableByDefaultEffects = false;


    public float cardCostNormal = 10f;
    CardDrawer cardDrawer;
    ManaDisplay manaDisplay;
    Text costText;
    ParticleSystem particleVFX;
    AudioSource audioCardDraw;
    public bool superCard = false;
    public bool superCardEnable = false;
    Material matCard;

    float currentCardType;
    public bool buttonPressed = false;
    public bool anyCardButton = false;
    
    IEnumerator Start()
    {
        matCard = GetComponent<SpriteRenderer>().material;
        particleVFX = GetComponentInChildren<ParticleSystem>();
        audioCardDraw = GetComponentInChildren<AudioSource>();
        cardDrawer = FindAnyObjectByType<CardDrawer>();
        manaDisplay = FindAnyObjectByType<ManaDisplay>();
        currentCardType = cardDrawer.GetCardType();
        costText = GetComponentInChildren<Text>();

        yield return new WaitForSeconds(2f);

        LabelButtonWithCost();
        DefaultEnable();
        DefaultEnableEffects();

    }

    private void DefaultEnable()
    {
        if (disabled == true)
        {
            return;
        }
        if (enableByDefault == true)
        {
            disabled = false;
            if(!anyCardButton)
            {
                DisableAllButtons();
            }
            SelectButton();
        }
    }

    private void DefaultEnableEffects()
    {
        if (enableByDefaultEffects == true)
        {
            if (particleVFX)
            {
                particleVFX.Play();
            }
            if (audioCardDraw)
            {
                audioCardDraw.Play();
            }
            GetComponent<SpriteRenderer>().color = Color.yellow;
            //matCard.SetColor("_Color", Color.yellow);
            //matCard.SetFloat("_NegativeAmount", 1f);
            //matCard.EnableKeyword("NEGATIVE_ON");
        }
    }

    private void LabelButtonWithCost()
    {
        if (cardType == 5 || cardType == 6 || cardType == 7 || cardType == 8 ||
            cardType == 9 || cardType == 10 || cardType == 11 || cardType == 12 ||
            cardType ==17 || cardType == 18 || (cardType >= 19 && cardType < 1000))
        {
            cardCostNormal = Mathf.Round(costMultiplier);
        }
        else if(cardType < 5)
        {
            cardCostNormal = Mathf.Round(costMultiplier);
        }
        else if(cardType == 13 || cardType == 14 || cardType == 15 || cardType == 16)
        {
            cardCostNormal = Mathf.Round(costMultiplier * (cardType - 12f));
        }
        else if(cardType > 1000f)
        {
            float cardTypeIter;
            float numberSelection = Mathf.Floor(cardType / 1000000f);
            cardTypeIter = cardType - numberSelection * 1000000f;
            float colorSelection = Mathf.Floor(cardTypeIter / 100000f);
            cardTypeIter = cardTypeIter - colorSelection * 100000f;
            float shapeSelection = Mathf.Floor(cardTypeIter / 10000f);
            cardTypeIter = cardTypeIter - shapeSelection * 10000f;
            float wordSelection = Mathf.Floor(cardTypeIter / 1000f);
            cardTypeIter = cardTypeIter - wordSelection * 1000f;
            float beatSelection = Mathf.Floor(cardTypeIter / 100f);
            cardTypeIter = cardTypeIter - beatSelection * 100f;
            float memorySelection = Mathf.Floor(cardTypeIter / 10f);
            cardTypeIter = cardTypeIter - memorySelection * 10f;
            float motorSelection = cardTypeIter;

            float numberOfActive = 0f;
            if(numberSelection > 1f)
            {
                numberOfActive++;
            }
            if (colorSelection > 1f)
            {
                numberOfActive++;
            }
            if (shapeSelection > 1f)
            {
                numberOfActive++;
            }
            if (wordSelection > 1f)
            {
                numberOfActive++;
            }
            if (beatSelection > 1f)
            {
                numberOfActive++;
            }
            if (memorySelection > 1f)
            {
                numberOfActive++;
            }
            if (motorSelection > 1f)
            {
                numberOfActive++;
            }

            cardCostNormal = Mathf.Round(costMultiplier * numberOfActive);
        }

        cardCost = cardCostNormal;
        cardCostSuper = Mathf.Round(4f * cardCostNormal);
        RefreshCostText();
        

    }

    private void RefreshCostText()
    {
        if(costText)
        {
            costText.text = cardCost.ToString();
        }
    }

    private void OnMouseDown()
    {
        if (disabled == true)
        {
            return;
        }

        DisableAllButtons();
        SelectButton();

    }

    private void SelectButton()
    {
        if (manaDisplay.manaValue >= cardCostNormal //manaDisplay.cardDrawThreshold * (cardType - 1)
                    && disabled == false)
        {
            if(particleVFX)
            {
                particleVFX.Play();
            }
            if(audioCardDraw)
            {
                audioCardDraw.Play();
            }
            
            if (superCard)
            {
                if(particleVFX)
                {
                    GetComponent<SpriteRenderer>().color = Color.yellow;
                    //matCard.SetFloat("_NegativeAmount", 1f);
                    //matCard.EnableKeyword("NEGATIVE_ON");
                }
                cardDrawer.SetCardType(cardType);
                cardCost = cardCostNormal;
                cardDrawer.SetCardCost(cardCost);
                cardDrawer.SetSuperCard(false);
                RefreshCostText();
                buttonPressed = true;
                superCard = false;
            }
            else
            {
                if (!buttonPressed || !superCardEnable)
                {
                    if (particleVFX)
                    {
                        GetComponent<SpriteRenderer>().color = Color.yellow;
                        //matCard.SetFloat("_NegativeAmount", 1f);
                        //matCard.EnableKeyword("NEGATIVE_ON");
                    }
                    
                    cardDrawer.SetCardType(cardType);
                    cardCost = cardCostNormal;
                    cardDrawer.SetCardCost(cardCost);
                    cardDrawer.SetSuperCard(false);
                    superCard = false;
                }
                else
                {
                    if (particleVFX)
                    {
                        GetComponent<SpriteRenderer>().color = Color.white;
                    }
                    cardDrawer.SetCardType(cardType);
                    cardCost = cardCostSuper;
                    superCard = true;
                    cardDrawer.SetCardCost(cardCost);
                    cardDrawer.SetSuperCard(true);
                    RefreshCostText();
                }
                buttonPressed = true;
            }

        }
    }


    private void DisableAllButtons()
    {
        var buttons = FindObjectsByType<BuyCardButton>(FindObjectsSortMode.None);
        foreach (BuyCardButton button in buttons)
        {
            button.GetComponent<SpriteRenderer>().color = new Color32(82, 82, 82, 0);
            if (button != this)
            {
                button.cardCost = button.cardCostNormal;
                button.buttonPressed = false;
                button.superCard = false;
                //button.RefreshCostText();
            }

        }
    }
}
