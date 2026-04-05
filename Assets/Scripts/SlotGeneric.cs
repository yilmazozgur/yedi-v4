using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;

public class SlotGeneric : MonoBehaviour
{
    private bool slotFilled = false;
    private Card cardAssigned;
    private Card cardObjectNull;
    Text slotManaText;
    SlotSell slotSell;
    bool slotSellFlag;
    public int slotNumber = 0;

    private void Start()
    {
        slotManaText = GetComponentInChildren<Text>();
        if(slotManaText)
        {
            slotManaText.text = " ";
        }
        
        slotSell = GetComponent<SlotSell>();
        slotSellFlag = slotSell != null;

        ComputeSlotNumber();
    }

    public void SetFilledInfo(bool filledSignal)
    {
        slotFilled = filledSignal;
    }

    public bool GetFilledInfo()
    {
        return slotFilled;
    }

    public void SetCardObject(Card cardSet)
    {
        cardAssigned = cardSet;
    }

    public Card GetCardObject()
    {
        return cardAssigned;
    }

    public void ComputeSlotNumber()
    {
        Slot1 slot1Object = GetComponent<Slot1>();
        if(slot1Object != null)
        {
            slotNumber = 1;
            return;
        }
        Slot2 slot2Object = GetComponent<Slot2>();
        if (slot2Object != null)
        {
            slotNumber = 2;
            return;
        }
        Slot3 slot3Object = GetComponent<Slot3>();
        if (slot3Object != null)
        {
            slotNumber = 3;
            return;
        }
        Slot4 slot4Object = GetComponent<Slot4>();
        if (slot4Object != null)
        {
            slotNumber = 4;
            return;
        }
        Slot5 slot5Object = GetComponent<Slot5>();
        if (slot5Object != null)
        {
            slotNumber = 5;
            return;
        }
    }

    public void UpdateManaValue()
    {
        if(slotManaText)
        {
            if (GetFilledInfo())
            {
                slotManaText.text = cardAssigned.GetCardMana().ToString();

            }
            else
            {
                slotManaText.text = " ";
            }
        }
        
        
    }

}
