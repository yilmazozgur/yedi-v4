using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class MemoryCard : CardTypeBase
{
    [SerializeField] public float memoryWaitTime = 2f;

    MemoryGenerator memoryGenerator;
    SpriteRenderer memoryIcon;
    SpriteRenderer noteDrawing;
    SpriteRenderer beatBox;
    SpriteRenderer motorBox;
    SpriteRenderer physicalDrawing;
    SpriteRenderer[] otherIcons;
    string modeMemory = "every action";
    CardFrameBackground cardFrameBackground;
    SpriteRenderer spriteRendererBG;
    Color backgroundColor;

    protected override void Start()
    {
        memoryIcon = GetComponentInChildren<SpriteRenderer>();
        if(memoryIcon)
        {
            memoryIcon.gameObject.SetActive(false);
        }

        otherIcons = GetComponentsInParent<SpriteRenderer>();
        foreach(SpriteRenderer iconIter in otherIcons)
        {
            if(iconIter.gameObject.name == "Note Drawing")
            {
                noteDrawing = iconIter;
            }
            if (iconIter.gameObject.name == "Beat Box")
            {
                beatBox = iconIter;
            }
            if (iconIter.gameObject.name == "Motor Box")
            {
                motorBox = iconIter;
            }
            if (iconIter.gameObject.name == "Physical Drawing")
            {
                physicalDrawing = iconIter;
            }
        }

        cardFrameBackground = GetComponentInParent<CardFrameBackground>();
        spriteRendererBG = cardFrameBackground.GetComponent<SpriteRenderer>();
        backgroundColor = spriteRendererBG.color;

        base.Start();
        memoryGenerator = FindAnyObjectByType<MemoryGenerator>();
        if (cardFrameAttached != null && cardFrameAttached.IsInitialized)
            return; // ActivateComponents() already set our values
        SetMemory();
    }

    public void SetMemory()
    {
        if (activated)
        {
            memoryGenerator.SetMemoryActivated(true);
            //StartCoroutine(HideCardInfo());
            
        }
    }

    IEnumerator HideCardInfo()
    {
        yield return new WaitForSeconds(memoryWaitTime);
        backgroundColor.a = 1f;
        spriteRendererBG.color = backgroundColor;
        spriteRendererBG.sortingOrder = 13;
        if (memoryIcon)
        {
            memoryIcon.gameObject.SetActive(true);
            //noteDrawing.gameObject.SetActive(false);
            //beatBox.gameObject.SetActive(false);
            //motorBox.gameObject.SetActive(false);
            //physicalDrawing.gameObject.SetActive(false);
        }
    }

    public void ShowCardInfo()
    {
        backgroundColor.a = 0.71f;
        spriteRendererBG.color = backgroundColor;
        spriteRendererBG.sortingOrder = 10;
        if (memoryIcon)
        {
            memoryIcon.gameObject.SetActive(false);
        }
        StartCoroutine(HideCardInfo());
    }

    public void ShowAllCardInfo()
    {
        MemoryCard[] memoryCards = FindObjectsByType<MemoryCard>(FindObjectsSortMode.None);
        foreach(MemoryCard memoryCard in memoryCards)
        {
            memoryCard.ShowCardInfo();
        }
    }

    public void MergeMemoryCard(float memoryGain)
    {
        if (activated)
        {
            if (modeMemory == "show one")
            {
                ShowCardInfo();
            }
            else //show all or every action
            {
                ShowAllCardInfo();
            }
            //Debug.Log(memoryGain);

            if (memoryGain < 0.7f)
            {
                cardAttached.ChangeCardMana(manaReductionMultiplier);
                return;
            }

            if (memoryGain >= 0.7f && memoryGain < 1.6f)
            {
                cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
                return;
            }

            if (memoryGain >= 1.6f && memoryGain < 2.7f)
            {
                cardAttached.ChangeCardMana(manaIncreaseMultiplier2);
                return;
            }

            if (memoryGain >= 2.7f)
            {
                cardAttached.ChangeCardMana(manaIncreaseMultiplier3);
                return;
            }

        }
    }

    public void SetActivated(bool activatedValue)
    {
        activated = activatedValue;
    }

    public void SetModeMemory(string modeMemorySet)
    {
        modeMemory = modeMemorySet;
    }

    public string GetModeMemory()
    {
        return modeMemory;
    }
}
