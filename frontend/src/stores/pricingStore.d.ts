export interface DisplayPlan {
    id: string;
    backendId: string;
    name: string;
    tagline: string;
    monthlyPrice: number;
    monthlyDisplay: string;
    annualPrice: number;
    annualDisplay: string;
    features: string[];
    ctaLabel: string;
    highlight?: boolean;
    isContactSales?: boolean;
    planType: 'individual' | 'venue';
}
export declare const usePricingStore: any;
