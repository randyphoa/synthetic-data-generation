public class CustomerClassifier {

    public String classify(int age, double income, boolean isMember) {
        if (age < 18) {
            return "junior";
        } else if (age >= 65) {
            if (isMember) {
                return "senior_member";
            } else {
                return "senior";
            }
        } else {
            if (income > 50000 && isMember) {
                return "premium";
            } else if (income > 50000) {
                return "standard_plus";
            } else {
                return "standard";
            }
        }
    }
}
