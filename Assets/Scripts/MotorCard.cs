using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using System.Linq;

public class MotorCard : CardTypeBase
{
    [SerializeField] float successNonlienarity = 0.7f;

    MotorGenerator motorGenerator;
    SpriteRenderer physicalRenderer;
    SpriteRenderer boxRenderer;
    string modeMotor = "speed accuracy";

    protected override void Start()
    {
        SpriteRenderer[] spriteRenderers = GetComponentsInChildren<SpriteRenderer>();
        foreach (SpriteRenderer spriteIter in spriteRenderers)
        {
            if (spriteIter.gameObject.name == "Motor Box")
            {
                boxRenderer = spriteIter;
                boxRenderer.gameObject.SetActive(false);
            }
            else if (spriteIter.gameObject.name == "Physical Drawing")
            {
                physicalRenderer = spriteIter;
                physicalRenderer.gameObject.SetActive(false);
            }
        }

        base.Start();
        motorGenerator = FindAnyObjectByType<MotorGenerator>();
        if (cardFrameAttached != null && cardFrameAttached.IsInitialized)
            return; // ActivateComponents() already set our values
        SetMotor();
    }

    public void SetMotor()
    {
        cardAttached = cardFrameAttached.cardObject;
    }

    public float MergeMotorCard(float timeSpannedDrop, float distanceDrop,
        float distanceToDroppedSlot, float halfDistanceToDroppedSlot, float[] minDistanceSlots)
    {
        float speedDropNormalized;
        float successDrop = 0f;
        float distanceToDroppedSlotNormalized = 0;
       
        if (modeMotor == "speed accuracy")
        {
            speedDropNormalized = Mathf.Pow(distanceDrop, successNonlienarity) / timeSpannedDrop;
            distanceToDroppedSlotNormalized = Mathf.Pow(distanceToDroppedSlot, 2.5f * successNonlienarity);
            successDrop = speedDropNormalized / (1f + distanceToDroppedSlotNormalized);
        }
        else if (modeMotor == "speed accuracy halfway")
        {
            speedDropNormalized = Mathf.Pow(20 + distanceDrop, successNonlienarity) / Mathf.Pow(timeSpannedDrop, 0.7f);
            distanceToDroppedSlotNormalized = Mathf.Pow((halfDistanceToDroppedSlot + distanceToDroppedSlot)/2f, 3f * successNonlienarity);
            successDrop = speedDropNormalized / (1f + distanceToDroppedSlotNormalized);
        }
        else if (modeMotor == "visit all slots")
        {
            speedDropNormalized = Mathf.Pow(30, successNonlienarity) / Mathf.Pow(timeSpannedDrop, 0.7f); //Fixed distance used since all slots are visited
            float averageDistance = ((float)minDistanceSlots.Sum()) / (float)minDistanceSlots.Length;
            //averageDistance = averageDistance  * 0.5f ; //Make it easier.
            distanceToDroppedSlotNormalized = Mathf.Pow(averageDistance, 2.5f * successNonlienarity);
            successDrop = speedDropNormalized / (1f + distanceToDroppedSlotNormalized);
        }


        if(modeMotor == "speed accuracy halfway")
        {
            successDrop = successDrop * 1.5f;  //Make it easier.
        }
        else if (modeMotor == "visit all slots")
        {
            successDrop = successDrop * 3.5f;  //Make it easier.
        }

        if (successDrop < 15f)
        {
            cardAttached.ChangeCardMana(manaReductionMultiplier);
            return -1f;
        }
        else if(successDrop >= 15f && successDrop < 21f)
        {
            return 0f;
        }
        else if (successDrop >= 21f && successDrop < 30f)
        {
            cardAttached.ChangeCardMana(manaIncreaseMultiplier1);
            return 1f;
        }
        else if (successDrop >= 30f && successDrop < 55f)
        {
            cardAttached.ChangeCardMana(manaIncreaseMultiplier2);
            return 2f;
        }
        else if (successDrop >= 55f)
        {
            cardAttached.ChangeCardMana(manaIncreaseMultiplier3);
            return 3f;
        }
        return 0f;
    }

    public void SetActivated(bool activatedValue)
    {
        activated = activatedValue;
        if (activated)
        {
            SetMotorIcon();
        }
    }

    private void SetMotorIcon()
    {
        boxRenderer.gameObject.SetActive(true);
        physicalRenderer.gameObject.SetActive(true);
    }

    public void SetModeMotor(string modeMotorSet)
    {
        modeMotor = modeMotorSet;
    }

    public string GetModeMotor()
    {
        return modeMotor;
    }

}
